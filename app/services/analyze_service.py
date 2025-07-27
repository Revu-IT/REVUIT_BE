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

# S3 설정
s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit"
FONT_PATH = os.path.join("fonts", "NanumGothic.ttf")

def generate_wordcloud_and_upload_from_csv(s3_key: str, sentiment: str, company_name: str) -> str:
    # S3에서 CSV 읽기
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response['Body'].read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    
    # 키워드 추출 및 카운트 (sentiment 필터링 포함)
    counter = Counter()
    for row in reader:
        label_raw = row.get("positive", "").strip()
        if not label_raw.isdigit():
            continue

        label = int(label_raw)

        if sentiment == "positive" and label != 1:
            continue
        if sentiment == "negative" and label != 0:
            continue

        keywords = row.get("keyword", "")
        for k in keywords.split(','):
            k = k.strip()
            if k:
                counter[k] += 1

    # 너무 적은 키워드 거르기
    filtered_counter = {k: v for k, v in counter.items() if v >= 2}
    if not filtered_counter:
        raise ValueError("조건에 맞는 키워드가 부족합니다.")

    # 상위 50개 키워드만 선택
    top_keywords = dict(Counter(filtered_counter).most_common(50))

    # 원형 마스크
    size = 800
    x, y = np.ogrid[:size, :size]
    mask = (x - size // 2) ** 2 + (y - size // 2) ** 2 > (size // 2) ** 2
    mask = 255 * mask.astype(int)

    # 6. 워드클라우드 생성
    wordcloud = WordCloud(
        font_path=FONT_PATH,
        background_color="white",
        width=size,
        height=size,
        mask=mask,
        colormap="tab10"
    ).generate_from_frequencies(top_keywords)

    # 이미지 저장 및 S3 업로드
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


# 상위 키워드별로 최신 리뷰 1개씩 반환
def get_top_keyword_reviews(s3_key: str, sentiment: str, top_k: int = 10) -> list:
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response["Body"].read().decode("utf-8")
    reader = list(csv.DictReader(io.StringIO(content)))

    # 키워드별 최신 리뷰 추출
    keyword_to_reviews = defaultdict(list)
    for row in reader:
        label = row.get("positive", "").strip()
        if sentiment == "positive" and label != "1":
            continue
        if sentiment == "negative" and label != "0":
            continue

        keywords = row.get("keyword", "")
        for k in keywords.split(","):
            k = k.strip()
            if k:
                keyword_to_reviews[k].append(row)

    # 키워드 등장 수 카운트
    keyword_counter = {k: len(v) for k, v in keyword_to_reviews.items()}
    top_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:top_k]

    result = []
    for keyword, _ in top_keywords:
        # 최신 날짜 기준 정렬
        keyword_reviews = keyword_to_reviews[keyword]
        sorted_reviews = sorted(keyword_reviews, key=lambda r: r.get("created_at", ""), reverse=True)
        latest = sorted_reviews[0] if sorted_reviews else {}
        result.append({
            "keyword": keyword,
            "latest_review": latest.get("content", "")
        })

    return result


# 특정 키워드에 해당하는 모든 리뷰 반환
def get_reviews_by_keyword(s3_key: str, keyword: str, segment: str = None) -> List[dict]:
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response["Body"].read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    results = []
    for row in reader:
        # sentiment 필터링 (segment == "positive" → positive == "1", segment == "negative" → positive == "0")
        label = row.get("positive", "").strip()
        if segment == "positive" and label != "1":
            continue
        if segment == "negative" and label != "0":
            continue

        keywords = [k.strip() for k in row.get("keyword", "").split(",")]
        if keyword in keywords:
            results.append({
                "content": row.get("content", ""),
                "created_at": row.get("date", "")
            })
    return results

