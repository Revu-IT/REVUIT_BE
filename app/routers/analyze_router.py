from fastapi import APIRouter, HTTPException, Depends, Query
from app.services.analyze_service import (
    generate_wordcloud,
    get_top_keyword_reviews,
    get_reviews_by_keyword,
    generate_wordcloud_for_all_companies,
    get_company_score_ranking,
    get_current_quarter_top_keywords,
)
from app.services.user_service import get_current_user
from app.models.user_model import User
from app.models.company_model import Company
from app.config.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/analyze", tags=["analyze"])

@router.get(
    "/wordcloud/{sentiment}",
    summary="소속 회사의 감성별 워드클라우드 생성 API",
    description="""
    현재 로그인된 사용자의 소속 회사 리뷰 데이터를 기반으로, 
    지정된 감성(긍정/부정)에 대한 워드클라우드를 생성하고 이미지 URL을 반환합니다.
    """
)
def get_wordcloud_for_company(
    sentiment: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if sentiment not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="sentiment는 'positive' 또는 'negative'여야 합니다.")

    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="소속 회사를 찾을 수 없습니다.")

    try:
        image_url = generate_wordcloud(db, current_user.company_id, sentiment, company.name)
        return {"image_url": image_url}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"워드클라우드 생성 중 서버 오류 발생: {e}")

@router.get(
    "/keywords/quarterly",
    summary="소속 회사 분기별 상위 키워드 조회 API",
    description="""
    현재 로그인된 사용자가 속한 회사의 리뷰 데이터를 기반으로, 
    현재 분기에 가장 많이 언급된 상위 4개의 키워드를 조회합니다.
    """
)
def get_top_keywords_by_quarter(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        quarterly_keywords = get_current_quarter_top_keywords(db, current_user.company_id, top_k=4)
        return {"data": quarterly_keywords}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분기별 키워드 분석 중 오류 발생: {e}")

@router.get(
    "/keywords/{sentiment}",
    summary="소속 회사의 감성별 상위 키워드 조회 API",
    description="""
    현재 로그인된 사용자의 소속 회사 리뷰 데이터를 기반으로, 
    지정된 감성(긍정/부정)에 따라 가장 빈번하게 나타나는 상위 10개 키워드와 그 빈도를 반환합니다.
    """
)
def get_top_keywords_by_sentiment(
    sentiment: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if sentiment not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="sentiment는 'positive' 또는 'negative'여야 합니다.")
    
    try:
        result = get_top_keyword_reviews(db, current_user.company_id, sentiment, top_k=10)
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"키워드 조회 중 오류 발생: {e}")


@router.get(
    "/reviews-by-keyword",
    summary="특정 키워드가 포함된 리뷰 조회 API",
    description="""
    현재 로그인된 사용자의 소속 회사 리뷰 데이터에서 특정 키워드를 포함하는 리뷰 목록을 조회합니다. 
    추가적으로 감성(긍정/부정)에 따라 필터링할 수 있습니다.
    """
)
def get_reviews_list_by_keyword(
    keyword: str = Query(..., min_length=1, description="검색할 키워드"),
    sentiment: str = Query(None, description="positive 또는 negative 중 하나"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if sentiment and sentiment not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="sentiment는 'positive' 또는 'negative'여야 합니다.")
    
    try:    
        reviews = get_reviews_by_keyword(db, current_user.company_id, keyword, sentiment)
        return {"keyword": keyword, "sentiment": sentiment, "reviews": reviews}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 조회 중 오류 발생: {e}")


@router.get(
    "/wordcloud/all/{sentiment}",
    summary="전체 회사 대상 3개월 워드클라우드 생성 API",
    description="""
    전체 회사의 최근 3개월 리뷰 데이터에 대한 워드클라우드를 생성하고 이미지 URL을 반환합니다. 
    감성(긍정/부정)을 지정할 수 있습니다.
    """
)
def get_all_companies_wordcloud(
    sentiment: str,
    db: Session = Depends(get_db)
):
    if sentiment not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="sentiment는 'positive' 또는 'negative'여야 합니다.")

    try:
        image_url = generate_wordcloud_for_all_companies(db, sentiment)
        return {"image_url": image_url}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전체 워드클라우드 생성 중 오류 발생: {e}")

@router.get(
    "/scores/ranking",
    summary="전체 회사별 평균 점수 및 순위 조회 API",
    description="""
    전체 회사의 리뷰 평균 점수를 계산하고 순위를 매겨 반환합니다.
    """
)
def get_score_ranking(db: Session = Depends(get_db)):
    try:
        ranking_data = get_company_score_ranking(db)
        return {"data": ranking_data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"점수 순위 계산 중 오류 발생: {e}")
