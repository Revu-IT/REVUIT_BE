import os
import re
import io
import csv
import uuid
import numpy as np
from collections import Counter, defaultdict
from typing import List, Dict
from datetime import datetime, timedelta

# 워드클라우드 관련 라이브러리
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# AWS S3 클라이언트
from app.config.s3 import get_s3_client

# S3 설정
s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit" # 실제 버킷 이름
FONT_PATH = os.path.join("fonts", "NanumGothic.ttf") # 폰트 경로

# --------------------------------------------------------------------------
# Helper Function
# --------------------------------------------------------------------------
def list_s3_csv_files_in_prefix(prefix: str) -> List[str]:
    """S3의 특정 폴더(prefix)에 있는 모든 CSV 파일 목록을 반환합니다."""
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
    csv_files = []
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj.get("Key")
            # 폴더가 아닌 실제 CSV 파일만 추가
            if key and key.endswith(".csv"):
                csv_files.append(key)
    print(f"Found {len(csv_files)} CSV files in '{prefix}'.")
    return csv_files

# --------------------------------------------------------------------------
# 1. 개별 회사 분석 기능
# --------------------------------------------------------------------------

def generate_wordcloud_and_upload_from_csv(s3_key: str, sentiment: str, company_name: str) -> str:
    """개별 회사의 CSV를 읽어 워드클라우드를 생성하고 S3에 업로드합니다."""
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response['Body'].read().decode('utf-8-sig')  # BOM 제거
    reader = csv.DictReader(io.StringIO(content))
    
    counter = Counter()
    three_months_ago = datetime.now() - timedelta(days=90)

    for row in reader:
        # 날짜 필터링 (최근 3개월)
        try:
            review_date_str = row.get("date", "").strip()  # BOM 제거 후 정상 접근
            if not review_date_str:
                continue
            
            # 시간 정보 포함된 날짜 형식 처리
            review_date = datetime.strptime(review_date_str, '%Y-%m-%d %H:%M:%S')
            if review_date < three_months_ago:
                continue
        except ValueError:
            continue

        # 감성 필터링
        try:
            label = float(row.get("positive", ""))
        except (ValueError, TypeError):
            continue
        if (sentiment == "positive" and label not in [1, 1.0]) or (sentiment == "negative" and label not in [0, 0.0]):
            continue

        # 텍스트 필터링
        text_content = row.get("cleaned_text")
        if not text_content or not text_content.strip():
            continue
        
        # 키워드 수집
        for k in text_content.split():
            k = k.strip()
            if k:
                counter[k] += 1
    
    # 키워드가 없을 경우 에러 발생
    if not counter:
        raise ValueError("최근 3개월간 조건에 맞는 키워드가 없습니다.")

    # 워드클라우드 생성
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

    # 이미지 변환 및 S3 업로드
    img_bytes = io.BytesIO()
    plt.figure(figsize=(8, 8))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(img_bytes, format='png', bbox_inches='tight', pad_inches=0)
    img_bytes.seek(0)

    file_name = f"wordcloud/{company_name}/{sentiment}/{uuid.uuid4()}.png"
    s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=img_bytes, ContentType='image/png')
    
    return f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{file_name}"


def get_top_keyword_reviews(s3_key: str, sentiment: str, top_k: int = 10) -> list:
    """개별 회사의 상위 키워드와 최신 리뷰를 반환합니다."""
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response['Body'].read().decode('utf-8-sig')
    reader = list(csv.DictReader(io.StringIO(content)))

    keyword_to_reviews = defaultdict(list)
    three_months_ago = datetime.now() - timedelta(days=90)

    for row in reader:
        # 날짜 필터링
        try:
            review_date_str = row.get("date", "").split(" ")[0]
            review_date = datetime.strptime(review_date_str, '%Y-%m-%d')
            if review_date < three_months_ago:
                continue
        except (ValueError, IndexError):
            continue
        
        # 감성 필터링
        try:
            label = int(float(row.get("positive", "")))
        except (ValueError, TypeError):
            continue
        if (sentiment == "positive" and label != 1) or (sentiment == "negative" and label != 0):
            continue

        text_content = row.get("cleaned_text")
        if not text_content:
            continue
            
        for k in text_content.split():
            k = k.strip()
            if k:
                keyword_to_reviews[k].append(row)

    keyword_counter = {k: len(v) for k, v in keyword_to_reviews.items()}
    top_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:top_k]

    result = []
    for keyword, _ in top_keywords:
        keyword_reviews = keyword_to_reviews[keyword]
        sorted_reviews = sorted(keyword_reviews, key=lambda r: r.get("date", ""), reverse=True)
        latest = sorted_reviews[0] if sorted_reviews else {}
        result.append({
            "keyword": keyword,
            "latest_review": latest.get("content", "")
        })
    return result

def get_reviews_by_keyword(s3_key: str, keyword: str, segment: str = None) -> List[dict]:
    """개별 회사에서 특정 키워드가 포함된 리뷰 목록을 반환합니다."""
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response['Body'].read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    results = []
    three_months_ago = datetime.now() - timedelta(days=90)

    for row in reader:
        # 날짜 필터링
        try:
            review_date_str = row.get("date", "").split(" ")[0]
            review_date = datetime.strptime(review_date_str, '%Y-%m-%d')
            if review_date < three_months_ago:
                continue
        except (ValueError, IndexError):
            continue
        
        # 감성 필터링
        try:
            label = int(float(row.get("positive", "")))
        except (ValueError, TypeError):
            continue
        if (segment == "positive" and label != 1) or (segment == "negative" and label != 0):
            continue

        words_in_row = row.get("cleaned_text", "").split()
        if keyword in words_in_row:
            results.append({
                "content": row.get("content", ""),
                "date": row.get("date", "")
            })
    return results

# --------------------------------------------------------------------------
# 2. 전체 회사 통합 분석 기능
# --------------------------------------------------------------------------

def generate_wordcloud_for_all_companies(sentiment: str) -> str:
    """S3 'airflow/' 폴더의 모든 CSV를 종합해 전체 워드클라우드를 생성합니다."""
    all_csv_keys = list_s3_csv_files_in_prefix("airflow/")
    if not all_csv_keys:
        raise ValueError("S3 'airflow/' 경로에 분석할 CSV 파일이 없습니다.")

    master_counter = Counter()
    three_months_ago = datetime.now() - timedelta(days=90)

    for s3_key in all_csv_keys:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            try:
                review_date_str = row.get("date", "").split(" ")[0]
                review_date = datetime.strptime(review_date_str, '%Y-%m-%d')
                if review_date < three_months_ago:
                    continue
            except (ValueError, IndexError):
                continue
            
            try:
                label = int(float(row.get("positive", "")))
            except (ValueError, TypeError):
                continue
            if (sentiment == "positive" and label != 1) or (sentiment == "negative" and label != 0):
                continue
            
            text_content = row.get("cleaned_text")
            if not text_content:
                continue
                
            for k in text_content.split():
                k = k.strip()
                if k:
                    master_counter[k] += 1
    
    if not master_counter:
        raise ValueError("최근 3개월간 조건에 맞는 키워드가 전체 회사에 걸쳐 없습니다.")

    top_keywords = dict(master_counter.most_common(50))
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
    
    file_name = f"wordcloud/ALL/{sentiment}/{uuid.uuid4()}.png"
    s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=img_bytes, ContentType='image/png')
    
    return f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{file_name}"


def get_company_score_ranking() -> List[Dict]:
    """
    S3 'airflow/' 폴더의 모든 CSV를 읽어, 회사별 'positive' 필드 평균 점수를 계산하고 순위를 매깁니다.
    """
    import re
    import csv
    import io
    from typing import List, Dict

    # S3에서 'airflow/' 디렉토리의 모든 CSV 파일 가져오기
    all_csv_keys = list_s3_csv_files_in_prefix("airflow/")
    if not all_csv_keys:
        raise ValueError("S3 'airflow/' 경로에 분석할 CSV 파일이 없습니다.")

    company_positive_averages = {}

    for s3_key in all_csv_keys:
        # 파일 이름에서 회사 이름 추출
        match = re.search(r'airflow/(.+)\.csv', s3_key)
        if not match:
            print(f"파일 이름에서 회사 이름을 추출할 수 없습니다: {s3_key}")
            continue
        company_name = match.group(1)

        # S3에서 파일 내용 읽기
        try:
            response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
            content = response['Body'].read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
        except Exception as e:
            print(f"S3 파일 읽기 실패: {s3_key}, 에러: {e}")
            continue

        positive_sum = 0.0
        total_reviews = 0

        # CSV 데이터 처리
        for row in reader:
            try:
                # 'positive' 필드가 존재하지 않으면 경고 출력
                if "positive" not in row:
                    print(f"누락된 'positive' 필드: {row}")
                    continue
                
                # 'positive' 필드 값을 가져옴 
                positive_value = float(row.get("positive", 0))
                positive_sum += positive_value
                total_reviews += 1
            except (ValueError, TypeError, AttributeError) as e:
                print(f"데이터 처리 중 에러 발생: {row}, 에러: {e}")
                continue
        
        # 회사별 'positive' 평균 계산
        if total_reviews > 0:
            positive_average = positive_sum / total_reviews
            company_positive_averages[company_name] = positive_average
            print(f"회사: {company_name}, 총 'positive' 점수: {positive_sum:.2f}, 리뷰 수: {total_reviews}, 평균 'positive': {positive_average:.2f}")
        else:
            print(f"회사: {company_name}에 리뷰 데이터가 없습니다.")

    if not company_positive_averages:
        raise ValueError("'positive' 점수를 계산할 수 있는 데이터가 없습니다.")

    # 'positive' 평균 점수가 높은 순으로 정렬
    sorted_companies = sorted(company_positive_averages.items(), key=lambda item: item[1], reverse=True)

    ranked_results = []
    for i, (company, avg_positive) in enumerate(sorted_companies):
        ranked_results.append({
            "rank": i + 1,
            "company_name": company,
            "positive_average": round(avg_positive, 2)  # 평균 점수를 소수점 둘째 자리까지 반올림
        })

    return ranked_results


def get_current_quarter_top_keywords(s3_key: str, top_k: int = 4) -> List[str]:
    """
    S3 리뷰 데이터에서 '현재 분기'에 해당하는 데이터만 필터링하여
    상위 키워드 리스트를 반환합니다.
    """
    # 현재 분기
    now = datetime.now()
    current_year = now.year
    current_quarter = (now.month - 1) // 3 + 1 

    # S3에서 CSV 파일 읽기
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response['Body'].read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    # 현재 분기의 키워드 빈도를 저장할 Counter
    keyword_counter = Counter()

    for row in reader:
        try:
            # 날짜 파싱
            review_date_str = row.get("date", "").split(" ")[0]
            review_date = datetime.strptime(review_date_str, '%Y-%m-%d')

            # 2. 리뷰 날짜가 현재 분기에 속하는지 확인
            review_year = review_date.year
            review_quarter = (review_date.month - 1) // 3 + 1

            # 올해, 현재 분기 데이터가 아니면 건너뛰기
            if not (review_year == current_year and review_quarter == current_quarter):
                continue

            # 정제된 텍스트에서 키워드 추출 및 카운트
            text_content = row.get("cleaned_text")
            if text_content:
                keywords = [k.strip() for k in text_content.split() if k.strip()]
                keyword_counter.update(keywords)

        except (ValueError, IndexError):
            # 날짜 형식이 잘못된 경우 건너뛰기
            continue

    if not keyword_counter:
        raise ValueError("현재 분기에 해당하는 리뷰 데이터가 없습니다.")

    # 3. 가장 많이 나온 키워드 K개를 리스트로 반환
    top_items = keyword_counter.most_common(top_k)
    return [keyword for keyword, freq in top_items]