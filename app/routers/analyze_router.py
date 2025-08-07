from fastapi import APIRouter, HTTPException, Depends, Query
from app.services.analyze_service import (
    get_top_keyword_reviews,
    get_reviews_by_keyword,
    generate_wordcloud_and_upload_from_csv
)
from app.services.user_service import get_current_user
from app.models.user_model import User
from app.config.database import get_db
from sqlalchemy.orm import Session
from app.utils.s3_util import get_s3_company_review

router = APIRouter(prefix="/analyze", tags=["analyze"])

# 회사 ID와 이름을 매핑하는 딕셔너리
COMPANY_MAP = {
    1: "coupang",
    2: "aliexpress",
    3: "gmarket",
    4: "11st",
    5: "temu"
}

@router.get("/wordcloud/{sentiment}")
def get_wordcloud(
    sentiment: str,
    current_user: User = Depends(get_current_user)
):
    if sentiment not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="sentiment는 'positive' 또는 'negative'여야 합니다.")

    try:
        # company_name 직접 조회
        company_name = COMPANY_MAP.get(current_user.company_id)
        if not company_name:
            raise HTTPException(status_code=400, detail="유효하지 않은 회사 ID")

        # get_s3_company_review 함수로부터 s3_key만 받기
        s3_key = get_s3_company_review(current_user)
        
    except HTTPException as e:
        raise e

    try:
        # 서비스 함수에 s3_key와 company_name을 각각 전달
        image_url = generate_wordcloud_and_upload_from_csv(s3_key, sentiment, company_name)
        return {"image_url": image_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/keywords/{sentiment}")
def top_keyword_reviews(
    sentiment: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        s3_key = get_s3_company_review(current_user)
    except HTTPException as e:
        raise e

    result = get_top_keyword_reviews(s3_key, sentiment, top_k=10)
    return {"data": result}


@router.get("/reviews-by-keyword")
def reviews_by_keyword(
    keyword: str = Query(...),
    segment: str = Query(None, description="positive 또는 negative 중 하나"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if segment and segment not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="segment는 'positive' 또는 'negative'여야 합니다.")

    try:
        s3_key = get_s3_company_review(current_user)
    except HTTPException as e:
        raise e
        
    reviews = get_reviews_by_keyword(s3_key, keyword, segment)
    return {"keyword": keyword, "segment": segment, "reviews": reviews}