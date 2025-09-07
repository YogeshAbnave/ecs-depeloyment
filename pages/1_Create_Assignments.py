import json, logging, math, random, time, base64
from io import BytesIO

import boto3, numpy as np, streamlit as st
from PIL import Image
from botocore.exceptions import ClientError
from components.Parameter_store import S3_BUCKET_NAME


# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb_client = boto3.resource("dynamodb")
bedrock_client = boto3.client("bedrock-runtime")
questions_table = dynamodb_client.Table("assignments")
user_name = "CloudAge-User"

text_model_id = "amazon.nova-pro-v1:0"
image_model_id = "amazon.nova-canvas-v1:0"

# Initialize stable session state keys
st.session_state.setdefault("input_text", "")
st.session_state.setdefault("question_answers", [])
st.session_state.setdefault("uploaded_image_bytes", None)
st.session_state.setdefault("selected_question_idx", None)
st.session_state.setdefault("reading_material", None)


# Method to call the foundation model
def query_generate_questions_answers_endpoint(input_text):
    prompt = f"{input_text}\n Using the above context, please generate five questions and answers you could ask students about this information."
    prompt = (
        prompt
        + "\nFormat the output as a list of five JSON objects containing the keys: Id, Question, and Answer"
    )
    input_data = {
        "inferenceConfig": {"max_new_tokens": 1000},
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
    }
    try:
        qa_response = bedrock_client.invoke_model(
            modelId=text_model_id,
            body=json.dumps(input_data).encode("utf-8"),
            accept="application/json",
            contentType="application/json",
        )
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{text_model_id}'. Reason: {e}")
        exit(1)

    response_body = json.loads(qa_response.get("body").read().decode())
    response_text = response_body["output"]["message"]["content"][0]["text"]

    return parse_text_to_lines(response_text)


# method to call the Titan image foundation model
def query_generate_image_endpoint(input_text):
    seed = np.random.randint(1000)
    input_body = json.dumps(
        {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": f"An image of {input_text}"},
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "height": 1024,
                "width": 1024,
                "cfgScale": 8.0,
                "seed": 0,
            },
        }
    )
    if image_model_id == "<model-id>":
        return None
    else:
        titan_image_api_response = bedrock_client.invoke_model(
            body=input_body,
            modelId=image_model_id,
            accept="application/json",
            contentType="application/json",
        )
        response_body = json.loads(titan_image_api_response.get("body").read())

        base64_image = response_body.get("images")[0]
        base64_bytes = base64_image.encode("ascii")
        image_bytes = base64.b64decode(base64_bytes)

        image = Image.open(BytesIO(image_bytes))
        return image


def generate_assignment_id_key():
    # Milliseconds since epoch
    epoch = round(time.time() * 1000)
    epoch = epoch - 1670000000000
    rand_id = math.floor(random.random() * 999)
    return (epoch * 1000) + rand_id


# create a function to load a file to S3 bucket
def load_file_to_s3(file_name, object_name):
    # Upload the file
    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(file_name, S3_BUCKET_NAME, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


# create a function to insert a record to DynamoDB table created_images
def insert_record_to_dynamodb(assignment_id, prompt, s3_image_name, data):
    # Ensure HASH key 'id' is present per table schema
    questions_table.put_item(
        Item={
            "id": assignment_id,
            "assignment_id": assignment_id,
            "teacher_id": user_name,
            "prompt": prompt,
            "s3_image_name": s3_image_name,
            "question_answers": data,
        }
    )


# Parse a string of text into a JSON dictionary object
def parse_text_to_lines(text):
    text = text.replace("```json\n", "").replace("\n```", "")
    lines = text.split("\n")
    lines = [line.strip() for line in lines]
    data = json.loads(text)

    return data


# Page configuration
st.set_page_config(page_title="Create Assignments", page_icon=":pencil:", layout="wide")

# Sidebar
st.sidebar.header("Create Assignments")

# Rest of the page
st.markdown("# Create Assignments")
st.sidebar.header("Input text to create assignments")

text = st.text_area("Input Text", key="input_text")
if (
    text
    and text != st.session_state.get("last_processed_input_text", None)
    and text != "None"
):
    try:
        if image_model_id != "<model-id>":
            image = query_generate_image_endpoint(text)
            image.save("temp-create.png")
            st.session_state["last_processed_input_text"] = text

        # generate questions and answer
        questions_answers = query_generate_questions_answers_endpoint(text)
        # st.write(questions_answers)
        st.session_state["question_answers"] = questions_answers
    except Exception as ex:
        st.error(f"There was an error while generating question. {ex}")

if st.session_state.get("question_answers", None):
    st.markdown("## Generated Questions and Answers")
    questions_answers = st.text_area(
        "Questions and Answers",
        json.dumps(st.session_state["question_answers"], indent=4),
        height=320,
        label_visibility="collapsed",
    )

if st.button("Generate Questions and Answers", key="btn_generate_qna"):
    st.session_state["question_answers"] = query_generate_questions_answers_endpoint(
        text
    )
    st.experimental_rerun()

if st.session_state.get("input-text", None):
    if image_model_id != "<model-id>":
        images = Image.open("temp-create.png")
        st.image(images, width=512)

if image_model_id != "<model-id>":
    if st.button("Generate New Image", key="btn_new_image"):
        image = query_generate_image_endpoint(text)
        image.save("temp-create.png")
        st.experimental_rerun()

st.markdown("------------")
if st.button("Save Question", key="btn_save_question"):
    # Check if we have questions and answers to save
    if not st.session_state.get("question_answers", None):
        st.error("Please generate questions and answers first!")
    elif not text:
        st.error("Please enter input text first!")
    else:
        try:
            # Generate assignment ID and prepare questions_answers for both cases
            assignment_id = str(generate_assignment_id_key())
            questions_answers = json.dumps(
                st.session_state["question_answers"], indent=4
            )

            if image_model_id != "<model-id>":
                # Image creation path
                object_name = f"generated_images/{assignment_id}.png"
                validation_object_name = f"generated_images/temp-create.png"

                # Check if temp image exists before uploading
                import os

                if os.path.exists("temp-create.png"):
                    load_file_to_s3("temp-create.png", object_name)
                    load_file_to_s3("temp-create.png", validation_object_name)
                    st.success(
                        f"Image generated and uploaded successfully: {object_name}"
                    )
                else:
                    st.warning("No image found to upload. Proceeding without image.")
                    object_name = "no image created"
            else:
                # No image creation path
                object_name = "no image created"

            # Insert record to DynamoDB
            insert_record_to_dynamodb(
                assignment_id, text, object_name, questions_answers
            )
            st.success(
                f"Assignment created and saved successfully with ID: {assignment_id}"
            )

        except Exception as ex:
            st.error(f"Error saving assignment: {ex}")
