import csv, io
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
from fastapi import HTTPException
from app.config.s3 import get_s3_client
from app.schemas.review_schema import ReviewItem, CompanyQuarterSummaryResponse
from app.utils.ai_util import call_gpt_with_prompt, parse_summary_json, load_prompt

s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit"

COMPANY_MAP = {
    1: "coupang",
    2: "aliexpress",
    3: "gmarket",
    4: "11st",
    5: "temu"
}

summary_prompt_path = "app/prompts/main_summary_prompt.txt"

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
            for month, scores in sorted(score_dict.items())
            if scores
        }

    return {
        "company_id": target_company_id,
        "review_count": total_review_count,
        "my_company_monthly_avg": compute_monthly_avg(monthly_scores_target),
        "industry_avg": compute_monthly_avg(monthly_scores_others),
    }

def get_company_reviews(user) -> List[ReviewItem]:
    company_name = COMPANY_MAP[user.company_id]
    key = f"airflow/{company_name}.csv"

    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    except Exception:
        return []

    content = response['Body'].read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    reviews = []
    for row in reader:
        try:
            review_date = datetime.strptime(row.get("date", ""), "%Y-%m-%d %H:%M:%S")
            positive = float(row.get("positive", 0)) == 1.0
            reviews.append(ReviewItem(
                content=row.get("content", ""),
                date=row.get("date", ""),
                score=row.get("score", ""),
                like=row.get("like", ""),
                positive=positive
            ))
        except Exception:
            continue
    return reviews

def get_quarterly_summary(user) -> CompanyQuarterSummaryResponse:
    reviews = get_company_reviews(user)
    if not reviews:
        return CompanyQuarterSummaryResponse(company=COMPANY_MAP[user.company_id], positive=True, summary="리뷰 데이터 없음")

    three_months_ago = datetime.now() - timedelta(days=90)
    recent_reviews = [r for r in reviews if datetime.strptime(r.date, "%Y-%m-%d %H:%M:%S") >= three_months_ago]

    pos_reviews = [r.content for r in recent_reviews if r.positive]
    neg_reviews = [r.content for r in recent_reviews if not r.positive]

    print(f"총 리뷰 개수: {len(recent_reviews)}")
    print(f"긍정 리뷰 개수: {len(pos_reviews)}")
    print(f"부정 리뷰 개수: {len(neg_reviews)}")

    majority_positive = len(pos_reviews) >= len(neg_reviews)
    target_texts = pos_reviews if majority_positive else neg_reviews

    if not target_texts:
        raise HTTPException(status_code=400, detail="최근 3개월 리뷰가 충분하지 않습니다.")

    review_list = "\n".join(f"- {t}" for t in target_texts)
    prompt_template = load_prompt(summary_prompt_path)

    summary_text = ""
    for attempt in range(1, 6):
        prompt = prompt_template.format(
            sentiment="긍정" if majority_positive else "부정",
            review_list=review_list
        )
        ai_response = call_gpt_with_prompt(prompt, max_tokens=200).strip()

        if ai_response.endswith("."):
            ai_response = ai_response[:-1].strip()

        if ai_response.endswith("다"):
            summary_text = ai_response
            break
        else:
            print(f"⚠️ 요약 문장이 조건에 맞지 않아 재생성 시도 {attempt}")

    if not summary_text:
        summary_text = ai_response

    return CompanyQuarterSummaryResponse(
        company=COMPANY_MAP[user.company_id],
        positive=majority_positive,
        summary=summary_text
    )