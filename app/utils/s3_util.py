import boto3
from fastapi import HTTPException
from app.models.user_model import User
from app.config.s3 import get_s3_client

s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit"

def get_s3_company_review(user: User) -> str:
    company_map = {
        1: "coupang",
        2: "aliexpress",
        3: "gmarket",
        4: "11st",
        5: "temu"
    }
    company_name = company_map.get(user.company_id)
    if not company_name:
        raise HTTPException(status_code=400, detail="유효하지 않은 회사 ID")

    response = s3.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=f"airflow/{company_name}.csv"
    )

    if "Contents" not in response:
        raise HTTPException(status_code=404, detail="파일이 없습니다")

    for obj in response["Contents"]:
        key = obj["Key"]
        if key.endswith(".csv"):
            return key

    raise HTTPException(status_code=404, detail="CSV 파일을 찾을 수 없습니다")
