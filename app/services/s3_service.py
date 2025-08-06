from botocore.exceptions import NoCredentialsError
from app.config.config import settings
from app.config.s3 import get_s3_client
from app.config.errors import ErrorMessages
import uuid

def upload_to_s3(bucket_name: str, folder_name: str, file_name: str, file_content: bytes):
    try:
        unique_filename = f"{uuid.uuid4()}_{file_name}"

        s3_file_path = f"{folder_name}/{unique_filename}"

        s3 = get_s3_client()
        s3.put_object(Bucket=bucket_name, Key=s3_file_path, Body=file_content)

        file_url = f"https://{bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_file_path}"

        return file_url

    except NoCredentialsError:
        return ErrorMessages.INVALID_S3_AUTHENTICATION

def list_all_s3_csv_files() -> list:
    s3 = get_s3_client()
    result = []
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=settings.AWS_BUCKET_NAME)

    for page in pages:
        contents = page.get("Contents", [])
        for obj in contents:
            key = obj["Key"]
            if key.endswith(".csv"):
                result.append(key)
    return result