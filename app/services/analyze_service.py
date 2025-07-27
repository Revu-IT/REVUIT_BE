import os
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import io
import uuid
import csv
from app.config.s3 import get_s3_client

s3 = get_s3_client()
BUCKET_NAME = "hanium-reviewit"
FONT_PATH = os.path.join("fonts", "NanumGothic.ttf")

def generate_wordcloud_and_upload_from_csv(s3_key: str, sentiment: str, company_name: str) -> str:
    # S3에서 CSV 읽기
    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content = response['Body'].read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))

    # 키워드 추출 및 카운트
    counter = Counter()
    for row in reader:
        label = row.get("positive")
        if sentiment == "positive" and label != "1":
            continue
        if sentiment == "negative" and label != "0":
            continue

        keywords = row.get("keyword", "")
        for k in keywords.split(','):
            k = k.strip()
            if k:
                counter[k] += 1

    # 너무 적은 키워드 거르기
    filtered_counter = {k: v for k, v in counter.items() if v >= 5}
    if not filtered_counter:
        raise ValueError("조건에 맞는 키워드가 부족합니다.")

    # 원형 마스크
    size = 800
    x, y = np.ogrid[:size, :size]
    mask = (x - size // 2) ** 2 + (y - size // 2) ** 2 > (size // 2) ** 2
    mask = 255 * mask.astype(int)

    # 워드클라우드 생성
    wordcloud = WordCloud(
        font_path=FONT_PATH,
        background_color="white",
        width=size,
        height=size,
        mask=mask,
        colormap="tab10"
    ).generate_from_frequencies(filtered_counter)

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
