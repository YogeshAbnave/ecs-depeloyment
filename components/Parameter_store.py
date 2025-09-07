import os

import streamlit as st

# Read bucket from environment, fallback to project bucket
S3_BUCKET_NAME = os.getenv("S3_BUCKET", "mcq-project")
