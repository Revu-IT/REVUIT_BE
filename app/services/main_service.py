import csv, io
from collections import defaultdict
from datetime import datetime
from typing import Dict
from fastapi import HTTPException
from app.config.s3 import get_s3_client


s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit"

COMPANY_MAP = {
    1: "coupang",
    2: "aliexpress",
    3: "gmarket",
    4: "11st",
    5: "temu"
}

def get_company_statistics(user) -> Dict:
    target_company_id = user.company_id
    target_company = COMPANY_MAP[target_company_id]

    monthly_scores_target = defaultdict(list)
    monthly_scores_others = defaultdict(list)
    total_review_count = 0

    for cid, company in COMPANY_MAP.items():
        key = f"airflow/{company}.csv"

        try:
            response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        except Exception:
            continue  # S3에 파일이 없으면 해당 회사는 스킵

        content = response['Body'].read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            try:
                date_str = row.get("date", "").strip()
                score_str = row.get("score", "").strip()
                if not date_str or not score_str:
                    continue

                # 전체 리뷰 수 count
                if cid == target_company_id:
                    total_review_count += 1

                # 2025년 리뷰만 월별 평균 계산
                date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

                if date_obj.year != 2025:
                    continue

                month = date_obj.month
                score = float(score_str)

                if cid == target_company_id:
                    monthly_scores_target[month].append(score)
                else:
                    monthly_scores_others[month].append(score)

            except Exception:
                continue

    def compute_monthly_avg(score_dict):
        return {
            month: round(sum(scores) / len(scores), 2)
            for month, scores in score_dict.items()
            if scores
        }

    return {
        "company_id": target_company_id,
        "review_count": total_review_count,
        "my_company_monthly_avg": compute_monthly_avg(monthly_scores_target),
        "industry_avg": compute_monthly_avg(monthly_scores_others),
    }