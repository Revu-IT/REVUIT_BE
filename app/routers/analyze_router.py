from fastapi import APIRouter, HTTPException, Depends, Query
from app.services.analyze_service import (
    get_top_keyword_reviews,
    get_reviews_by_keyword,
    generate_wordcloud_and_upload_from_csv,
    generate_wordcloud_for_all_companies,
    get_company_score_ranking,
    get_current_quarter_top_keywords
)
from app.services.user_service import get_current_user
from app.models.user_model import User
from app.config.database import get_db
from sqlalchemy.orm import Session
from app.utils.s3_util import get_s3_company_review
import re 

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


@router.get("/keywords/quarterly", summary="로그인된 사용자의 회사 분기별 상위 4개 키워드 조회하기")
def get_top_keywords_by_quarter(
    current_user: User = Depends(get_current_user)
):
    """
    현재 로그인된 사용자가 속한 회사의 리뷰 데이터를 기반으로,
    분기별 가장 많이 언급된 상위 4개의 키워드를 조회합니다.
    """

    print("in")
    try:
        # 현재 유저 정보로 S3 리뷰 파일 경로 가져오기
        s3_key = get_s3_company_review(current_user)
    except HTTPException as e:
        # 유저 정보가 유효하지 않거나 파일이 없을 경우
        raise e

    try:
        quarterly_keywords = get_current_quarter_top_keywords(s3_key, top_k=4)
        return {"data": quarterly_keywords}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분기별 키워드 분석 중 오류 발생: {e}")
    

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


@router.get("/wordcloud/all/{sentiment}", summary="전체 회사 대상 3개월 워드클라우드 생성")
def get_all_companies_wordcloud(
    sentiment: str,
):
    """
    S3 'airflow/' 경로의 모든 CSV 파일을 종합하여, 
    최근 3개월 데이터에 대한 워드클라우드를 생성합니다.
    """
    # 'sentiment' 파라미터가 'positive' 또는 'negative'가 맞는지 확인
    if sentiment not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="sentiment는 'positive' 또는 'negative'여야 합니다.")

    try:
        # 실제 로직을 담고 있는 서비스 함수를 호출.
        image_url = generate_wordcloud_for_all_companies(sentiment)
        
        # 성공 시, 이미지 URL을 JSON 형태로 반환
        return {"image_url": image_url}
    
    except ValueError as e:
        # 서비스에서 'ValueError'가 발생하면 (데이터가 없는 경우), 404 에러를 반환
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        # 그 외 예측하지 못한 에러가 발생하면, 500 에러를 반환
        raise HTTPException(status_code=500, detail=f"전체 워드클라우드 생성 중 오류 발생: {e}")
    

@router.get("/scores/ranking", summary="전체 회사별 평균 점수 및 순위")
def get_score_ranking():
    """
    S3 'airflow/' 경로의 모든 CSV 파일을 읽어, 
    각 회사별 리뷰의 평균 점수를 계산하고 순위를 반환합니다.
    """
    try:
        # 점수 순위 계산 서비스 호출
        ranking_data = get_company_score_ranking()
        return {"data": ranking_data}
    except ValueError as e:
        # 서비스에서 파일이나 데이터가 없다고 보낸 오류 처리
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # 기타 예상치 못한 서버 오류 처리
        raise HTTPException(status_code=500, detail=f"점수 순위 계산 중 오류 발생: {e}")
    
