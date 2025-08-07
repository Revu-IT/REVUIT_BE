import os
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
import io
import uuid
import csv
from typing import List, Dict
from app.config.s3 import get_s3_client
from datetime import datetime, timedelta

# S3 설정
s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit"
FONT_PATH = os.path.join("fonts", "NanumGothic.ttf")

def generate_wordcloud_and_upload_from_csv(s3_key: str, sentiment: str, company_name: str) -> str:
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response['Body'].read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    
    counter = Counter()
    # 3개월 전 날짜 계산
    three_months_ago = datetime.now() - timedelta(days=90)

    for row in reader:
        # 날짜 필터링 로직
        try:
            review_date_str = row.get("date", "").split(" ")[0]
            review_date = datetime.strptime(review_date_str, '%Y-%m-%d')
            if review_date < three_months_ago:
                continue # 3개월 이전 데이터는 건너뛰기
        except (ValueError, IndexError):
            continue # 날짜 형식이 잘못되었거나 없으면 건너뛰기

        # 감성 필터링
        try:
            label = int(float(row.get("positive", "")))
        except (ValueError, TypeError):
            continue
        if (sentiment == "positive" and label != 1) or (sentiment == "negative" and label != 0):
            continue

        text_content = row.get("cleaned_text", "")
        if not text_content:
            continue
        
        for k in text_content.split():
            k = k.strip()
            if k:
                counter[k] += 1
    
    if not counter:
        raise ValueError("조건에 맞는 키워드가 없습니다.")

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
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response["Body"].read().decode("utf-8")
    reader = list(csv.DictReader(io.StringIO(content)))

    keyword_to_reviews = defaultdict(list)
    # 3개월 전 날짜 계산
    three_months_ago = datetime.now() - timedelta(days=90)

    for row in reader:
        # 날짜 필터링 로직
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

        text_content = row.get("cleaned_text", "")
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
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response["Body"].read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    results = []
    # 3개월 전 날짜 계산
    three_months_ago = datetime.now() - timedelta(days=90)

    for row in reader:
        # 날짜 필터링 로직
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
        if (segment == "positive" and label != 1) or (segment == "negative" and label != 0):
            continue

        words_in_row = row.get("cleaned_text", "").split()
        if keyword in words_in_row:
            results.append({
                "content": row.get("content", ""),
                "date": row.get("date", "")
            })
    return results


# analyze_service.py 파일에 추가할 내용

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

def generate_wordcloud_for_all_companies(sentiment: str) -> str:
    """S3의 'airflow/' 폴더에 있는 모든 CSV를 종합해 워드클라우드를 생성합니다."""
    
    # 1. 'airflow/' 폴더의 모든 CSV 파일 경로 가져오기
    all_csv_keys = list_s3_csv_files_in_prefix("airflow/")
    if not all_csv_keys:
        raise ValueError("S3 'airflow/' 경로에 분석할 CSV 파일이 없습니다.")

    master_counter = Counter()
    three_months_ago = datetime.now() - timedelta(days=90)

    # 2. 모든 CSV 파일을 순회하며 데이터 처리
    for s3_key in all_csv_keys:
        print(f"--- Processing file: {s3_key} ---")
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            # 날짜 필터링 (최근 3개월)
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

            # 'cleaned_text' 필드 존재 여부 확인 및 예외 처리
            text_content = row.get("cleaned_text")
            if not text_content:
                continue # 필드가 없거나 비어있으면 다음 행으로

            # 키워드 카운팅
            for k in text_content.split():
                k = k.strip()
                if k:
                    master_counter[k] += 1
    
    # 3. 최종 키워드 유무 확인
    if not master_counter:
        raise ValueError("최근 3개월간 조건에 맞는 키워드가 전체 회사에 걸쳐 없습니다.")

    # 4. 워드클라우드 생성 및 업로드 (기존 로직과 유사)
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
    
    # 전체 회사용 경로에 저장
    file_name = f"wordcloud/ALL/{sentiment}/{uuid.uuid4()}.png"
    s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=img_bytes, ContentType='image/png')
    
    return f"https://{BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{file_name}"