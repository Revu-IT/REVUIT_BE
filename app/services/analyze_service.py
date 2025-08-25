import io
import uuid
import numpy as np
from collections import Counter
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import os
# 로깅
import logging 

# 워드클라우드
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# SQLAlchemy & DB Models
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.review_model import Review
from app.models.company_model import Company

# AWS S3 클라이언트
from app.config.s3 import get_s3_client

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# S3 설정
s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit"
FONT_PATH = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'NanumGothic.ttf')


# --------------------------------------------------------------------------
# Helper Function
# --------------------------------------------------------------------------
def get_quarter_dates(year: int, quarter: int) -> Tuple[datetime, datetime]:
    """주어진 연도와 분기의 시작일과 종료일을 반환합니다."""
    if not 1 <= quarter <= 4:
        raise ValueError("Quarter must be between 1 and 4.")
    
    start_month = 3 * quarter - 2
    start_date = datetime(year, start_month, 1)
    
    end_year = year
    end_month = start_month + 2
    
    # 해당 월의 마지막 날짜 계산
    import calendar
    last_day = calendar.monthrange(end_year, end_month)[1]
    end_date = datetime(end_year, end_month, last_day, 23, 59, 59)
    
    return start_date, end_date

# --------------------------------------------------------------------------
# 1. 개별 회사 분석 기능 (DB 조회)
# --------------------------------------------------------------------------

def generate_wordcloud(db: Session, company_id: int, sentiment: str, company_name: str) -> str:
    """DB에서 개별 회사의 리뷰를 읽어 워드클라우드를 생성하고 S3에 업로드합니다."""
    three_months_ago = datetime.now() - timedelta(days=90)
    is_positive = sentiment == "positive"

    reviews_texts = db.query(Review.cleaned_text).filter(
        Review.company_id == company_id,
        Review.positive == is_positive,
        Review.date >= three_months_ago,
        Review.cleaned_text.isnot(None)
    ).all()

    if not reviews_texts:
        logger.warning("No matching reviews found in the database for the given criteria.")
        raise ValueError("최근 3개월간 조건에 맞는 키워드가 없습니다.")

    counter = Counter()
    for (text,) in reviews_texts:
        for keyword in text.split():
            keyword = keyword.strip()
            if keyword:
                counter[keyword] += 1
    
    if not counter:
        raise ValueError("분석할 키워드가 없습니다.")

    top_keywords = dict(counter.most_common(50))
    size = 800
    x, y = np.ogrid[:size, :size]
    mask = (x - size // 2) ** 2 + (y - size // 2) ** 2 > (size // 2) ** 2
    mask = 255 * mask.astype(int)

    wordcloud = WordCloud(
        font_path=FONT_PATH,
        background_color="white",
        width=size,
        height=size,
        mask=mask,
        colormap="tab10"
    ).generate_from_frequencies(top_keywords)

    img_bytes = io.BytesIO()
    plt.figure(figsize=(8, 8))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(img_bytes, format='png', bbox_inches='tight', pad_inches=0)
    img_bytes.seek(0)

    file_name = f"wordcloud/{company_name}/{sentiment}/{uuid.uuid4()}.png"
    s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=img_bytes, ContentType='image/png')
    
    logger.info(f"Wordcloud successfully generated and uploaded to S3.")
    
    return f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{file_name}"

def get_top_keyword_reviews(db: Session, company_id: int, sentiment: str, top_k: int = 10) -> List[Dict]:
    """DB에서 개별 회사의 상위 키워드와 최신 리뷰를 반환합니다."""
    three_months_ago = datetime.now() - timedelta(days=90)
    is_positive = sentiment == "positive"
    
    reviews = db.query(Review).filter(
        Review.company_id == company_id,
        Review.positive == is_positive,
        Review.date >= three_months_ago,
        Review.cleaned_text.isnot(None)
    ).order_by(Review.date.desc()).all()

    if not reviews:
        return []

    keyword_to_reviews_counter = Counter()
    keyword_latest_review_content = {}

    for review in reviews:
        if not review.cleaned_text:
            continue
        
        unique_keywords_in_review = set(k.strip() for k in review.cleaned_text.split() if k.strip())
        for keyword in unique_keywords_in_review:
            keyword_to_reviews_counter[keyword] += 1
            if keyword not in keyword_latest_review_content:
                keyword_latest_review_content[keyword] = review.content

    top_keywords = keyword_to_reviews_counter.most_common(top_k)

    result = [
        {
            "keyword": keyword,
            "count": count,
            "latest_review": keyword_latest_review_content.get(keyword, "")
        }
        for keyword, count in top_keywords
    ]
    return result

def get_reviews_by_keyword(db: Session, company_id: int, keyword: str, sentiment: str = None) -> List[Dict]:
    """DB에서 특정 키워드가 포함된 리뷰 목록을 반환합니다."""
    three_months_ago = datetime.now() - timedelta(days=90)

    query = db.query(Review).filter(
        Review.company_id == company_id,
        Review.date >= three_months_ago,
        Review.cleaned_text.ilike(f"%{keyword}%") # 부분 문자열 검색
    )

    if sentiment:
        is_positive = sentiment == "positive"
        query = query.filter(Review.positive == is_positive)

    reviews = query.order_by(Review.date.desc()).all()
    
    return [
        {"content": review.content, "date": review.date.strftime('%Y-%m-%d %H:%M:%S')}
        for review in reviews
    ]

def get_current_quarter_top_keywords(db: Session, company_id: int, top_k: int = 4) -> List[str]:
    """현재 분기 데이터에 대한 상위 키워드 리스트를 반환합니다."""
    now = datetime.now()
    current_quarter = (now.month - 1) // 3 + 1
    start_date, end_date = get_quarter_dates(now.year, current_quarter)

    reviews_texts = db.query(Review.cleaned_text).filter(
        Review.company_id == company_id,
        Review.date.between(start_date, end_date),
        Review.cleaned_text.isnot(None)
    ).all()
    
    if not reviews_texts:
        raise ValueError("현재 분기에 해당하는 리뷰 데이터가 없습니다.")

    counter = Counter()
    for (text,) in reviews_texts:
        for keyword in text.split():
            keyword = keyword.strip()
            if keyword:
                counter[keyword] += 1

    if not counter:
        raise ValueError("분석할 키워드가 없습니다.")

    top_items = counter.most_common(top_k)
    return [keyword for keyword, freq in top_items]

# --------------------------------------------------------------------------
# 2. 전체 회사 통합 분석 기능 (DB 조회)
# --------------------------------------------------------------------------

def generate_wordcloud_for_all_companies(db: Session, sentiment: str) -> str:
    """DB에서 전체 회사의 리뷰를 종합해 워드클라우드를 생성합니다."""
    three_months_ago = datetime.now() - timedelta(days=90)
    is_positive = sentiment == "positive"

    reviews_texts = db.query(Review.cleaned_text).filter(
        Review.positive == is_positive,
        Review.date >= three_months_ago,
        Review.cleaned_text.isnot(None)
    ).all()

    if not reviews_texts:
        raise ValueError("최근 3개월간 조건에 맞는 키워드가 전체 회사에 걸쳐 없습니다.")

    counter = Counter()
    for (text,) in reviews_texts:
        for keyword in text.split():
            keyword = keyword.strip()
            if keyword:
                counter[keyword] += 1
    
    if not counter:
        raise ValueError("분석할 키워드가 없습니다.")

    top_keywords = dict(counter.most_common(50))
    size = 800
    x, y = np.ogrid[:size, :size]
    mask = (x - size // 2) ** 2 + (y - size // 2) ** 2 > (size // 2) ** 2
    mask = 255 * mask.astype(int)
    wordcloud = WordCloud(font_path=FONT_PATH, background_color="white", width=size, height=size, mask=mask, colormap="tab10").generate_from_frequencies(top_keywords)
    
    img_bytes = io.BytesIO()
    plt.figure(figsize=(8, 8))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(img_bytes, format='png', bbox_inches='tight', pad_inches=0)
    img_bytes.seek(0)
    
    file_name = f"wordcloud/ALL/{sentiment}/{uuid.uuid4()}.png"
    s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=img_bytes, ContentType='image/png')
    
    return f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{file_name}"

def get_company_score_ranking(db: Session) -> List[Dict]:
    """DB 쿼리를 통해 회사별 평균 점수를 계산하고 순위를 매깁니다."""
    
    results = db.query(
        Company.name.label("company_name"),
        func.avg(Review.score).label("average_score"),
        func.count(Review.id).label("review_count")
    ).join(Company, Review.company_id == Company.id).filter(
        Review.score.isnot(None)
    ).group_by(
        Company.name
    ).order_by(
        func.avg(Review.score).desc()
    ).all()
    
    if not results:
        raise ValueError("평균 점수를 계산할 리뷰 데이터가 없습니다.")

    ranked_results = [
        {
            "rank": i + 1,
            "company_name": row.company_name,
            "average_score": round(float(row.average_score), 2),
            "review_count": row.review_count
        }
        for i, row in enumerate(results)
    ]

    return ranked_results
