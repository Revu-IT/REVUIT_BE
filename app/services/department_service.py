import csv, io
from app.config.s3 import get_s3_client

s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit"

def get_department_reviews(s3_key: str, department: str) -> dict:
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response['Body'].read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    results = []
    pos_count = 0
    neg_count = 0

    for row in reader:
        if row.get("department") != department:
            continue

        sentiment_raw = row.get("positive", "").strip()
        is_positive = sentiment_raw in ("1", "1.0")
        is_negative = sentiment_raw in ("0", "0.0")

        if is_positive:
            pos_count += 1
        elif is_negative:
            neg_count += 1

        results.append({
            "content": row.get("content", ""),
            "date": row.get("date", ""),
            "score": row.get("score", ""),
            "like": row.get("like", ""),
        })

    return {
        "department": department,
        "positive_count": pos_count,
        "negative_count": neg_count,
        "reviews": results
    }
