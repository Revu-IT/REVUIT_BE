from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
import time
import anthropic
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.review_model import Review
from app.schemas.review_schema import ReviewItem, CompanyQuarterSummaryResponse
from app.utils.ai_util import call_ai_with_prompt, load_prompt

summary_prompt_path = "app/prompts/main_summary_prompt.txt"

def get_company_statistics(user, db: Session) -> Dict:
    target_company_id = user.company_id

    target_reviews = db.query(Review).filter(Review.company_id == target_company_id).all()
    other_reviews = db.query(Review).filter(Review.company_id != target_company_id).all()

    monthly_scores_target = defaultdict(list)
    monthly_scores_others = defaultdict(list)
    total_review_count = len(target_reviews)

    current_year = datetime.now().year

    def process_reviews(reviews, bucket):
        for r in reviews:
            if not r.date or not r.score:
                continue
            if r.date.year != current_year:
                continue
            month = r.date.month
            bucket[month].append(float(r.score))

    process_reviews(target_reviews, monthly_scores_target)
    process_reviews(other_reviews, monthly_scores_others)

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

def get_company_reviews(user, db: Session) -> List[ReviewItem]:
    reviews = db.query(Review).filter(Review.company_id == user.company_id).all()
    review_items = []

    for r in reviews:
        try:
            review_items.append(
                ReviewItem(
                    content=r.content or "",
                    date=r.date.strftime("%Y-%m-%d %H:%M:%S"),
                    score=float(r.score) if r.score is not None else None,
                    like=int(r.likes or 0),
                    positive=r.positive,
                )
            )
        except Exception:
            continue

    return review_items


def get_quarterly_summary(user, db: Session) -> CompanyQuarterSummaryResponse:
    reviews = get_company_reviews(user, db)
    if not reviews:
        return CompanyQuarterSummaryResponse(
            company=user.company.name,
            positive=True,
            summary="리뷰 데이터 없음",
        )

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
        try:
            prompt = prompt_template.format(
                sentiment="긍정" if majority_positive else "부정",
                review_list=review_list
            )
            ai_response = call_ai_with_prompt(prompt, max_tokens=200).strip()

            if ai_response.endswith("."):
                ai_response = ai_response[:-1].strip()

            words = ai_response.split()
            if ai_response.endswith("다") and len(words) <= 5:
                summary_text = ai_response
                print(f"✅ 요약 성공 (시도 {attempt}): {summary_text}")
                break
            else:
                print(f"⚠️ 요약 문장이 조건에 맞지 않아 재생성 시도 {attempt}: '{ai_response}'")

        except anthropic.RateLimitError:
            print(f"🔴 API Rate Limit 초과. 재시도 {attempt} 중단 후 Fallback 로직으로 전환합니다.")
            break
        
        except Exception as e:
            print(f"🔴 API 호출 중 알 수 없는 에러 발생: {e}")
            break

        if attempt < 5:
            time.sleep(1)

    if not summary_text:
        print("🔴 5번 시도 모두 실패. Fallback 로직을 실행합니다.")
        if majority_positive:
            summary_text = "편리하다"
        else:
            summary_text = "불편하다"

    return CompanyQuarterSummaryResponse(
        company=user.company.name,
        positive=majority_positive,
        summary=summary_text
    )