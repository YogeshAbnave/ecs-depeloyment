## CloudAge Education App - Project Guide

This document explains the project flow, components, and how to run and deploy the app in simple, clear steps.

### What the app does
- Teachers create English assignments (sentence, questions, image) and save them.
- Students select an assignment, answer questions, and get an AI-based score and suggestions.

### Main components
- `Home.py`: Landing page for Streamlit app.
- `pages/3_Complete_Assignments.py`: Student page to select an assignment, answer, and get scored.
- `components/Parameter_store.py`: Configuration helpers (e.g., S3 bucket name).
- `components/ui_template.py`: Shared Streamlit UI helpers (page setup, chrome hiding, headers).
- `ecs-task.json` and `aws/task-definition.json`: ECS task definitions for container runtime.
- `aws/` scripts: Infrastructure setup (ALB, target group, security groups), IAM roles.
- `quick-deploy.sh` / `quick-deploy.ps1`: One-command deploy scripts to ECR/ECS.
- `.streamlit/config.toml`: Unified Streamlit theme.

### Data flow (student answering)
1. Streamlit loads `Home.py` then navigates to `pages/3_Complete_Assignments.py`.
2. The page reads assignments from DynamoDB `assignments`.
3. The page downloads the assignment image from S3 and shows it.
4. Student selects a question and types an answer.
5. The app calls Amazon Bedrock to embed both answer and correct answer, then computes cosine similarity to produce a score.
6. It saves/upserts the best score per student/question to DynamoDB `answers` and shows top scores (via GSI `assignment_question_id-index`).
7. It calls Bedrock text models for suggested corrections and sentences.

### AWS resources used
- ECR: stores the Docker image.
- ECS Fargate: runs the container (`cloudage-task` → `cloudage-service` on `cloudage-cluster`).
- ALB: exposes the app publicly.
- DynamoDB: `assignments` and `answers` tables.
- S3: stores images.
- IAM: roles/policies for the ECS task and scripts.

### How deployment works (one command)
Both deploy scripts do the following safely and idempotently:
1. Login to ECR.
2. Build the Docker image, pre-pull base image with retries (resilient to slow network).
3. Tag and push the image to ECR with retry/backoff.
4. Ensure IAM inline policies are attached to `ecsTaskRole` (Bedrock + S3).
5. Ensure DynamoDB tables exist: `assignments` and `answers` (create `answers` + GSI if missing).
6. Ensure S3 bucket exists.
7. Register the ECS task definition from `ecs-task.json` if present.
8. Ensure the ECS service exists (create if missing) and is wired to ALB target group.
9. Force a new deployment on ECS, wait until stable, and print the app URL.

### Running locally
Prerequisites: Python 3.9+, `pip`.

```bash
pip install -r requirements.txt
streamlit run Home.py
```

### Deploying to AWS
Use either shell depending on your environment. Region is `us-east-1` by default.

PowerShell (Windows):
```powershell
.\n+ .\quick-deploy.ps1
```

Bash (Git Bash/WSL/macOS/Linux):
```bash
chmod +x quick-deploy.sh
./quick-deploy.sh
```

The scripts will print the ALB URL when complete.

### Configuration
- S3 bucket name is read via `components/Parameter_store.py` and passed to the app.
- Task definition environment variables (in `ecs-task.json`):
  - `ASSIGNMENTS_TABLE=assignments`
  - `AWS_REGION=us-east-1`
  - `BEDROCK_MODEL_ID=amazon.nova-canvas-v1:0`
  - `S3_BUCKET=mcq-project`

### Operational notes
- The deploy scripts are safe to run multiple times.
- They auto-create missing resources (answers table, ECS service) to avoid common errors.
- Network hiccups during Docker pulls are retried.

### Troubleshooting
- Service not found: scripts now create `cloudage-service` automatically.
- PutItem ResourceNotFound: scripts ensure `answers` table and GSI exist.
- Docker TLS timeout: scripts pre-pull base image and increase timeouts.

### Roadmap / structure
- Current code paths stay unchanged. A proposed structure is outlined in `commands.md` to migrate gradually (`app/`, `infra/`, `docker/`).


