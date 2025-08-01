import csv, io
from app.config.s3 import get_s3_client
from sqlalchemy.orm import Session
from app.models.department_model import Department
from app.config.errors import ErrorMessages

s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit"

def get_department_name_by_id(db: Session, department_id: int) -> str:
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise ValueError(ErrorMessages.INVALID_DEPARTMENT_ID)
    return department.name


def get_department_reviews(s3_key: str, department_name: str) -> dict:
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response['Body'].read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    results = []
    department_found = False

    for row in reader:
        if row.get("department", "").strip() != department_name:
            continue

        department_found = True

        results.append({
            "content": row.get("content", ""),
            "date": row.get("date", ""),
            "score": row.get("score", ""),
            "like": row.get("like", "")
        })

    if not department_found:
        raise ValueError(f"Department '{department_name}' not found in CSV.")

    return {
        "department_name": department_name,
        "reviews": results
    }
