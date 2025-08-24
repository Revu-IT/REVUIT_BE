import os
import re
import json
from typing import List, Tuple
from dotenv import load_dotenv
from openai import OpenAI
from app.schemas.review_schema import Summary, ReviewItem

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

summary_prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'summary_prompt.txt')
report_prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'report_prompt.txt')

def load_prompt(path: str) -> str:
    with open(path, encoding='utf-8') as f:
        return f.read()

def call_gpt_with_prompt(prompt: str, max_tokens: int = 700) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content.strip()
    print("🔹 GPT 응답:", content)
    return content
def extract_summary_topics(response_text: str) -> List[Tuple[str, int]]:
    topics = []
    for line in response_text.splitlines():
        if not line.strip():
            continue
        match = re.match(r"\d+\.\s*['\"]?(.+?)['\"]?\s*\((\d+)\s*개\)", line)
        if match:
            topic = match.group(1)
            count = int(match.group(2))
            topics.append((topic, count))
        else:
            topics.append((line.strip(), 0))  # fallback
    return topics

def build_summary(topics_with_counts: List[Tuple[str, int]]) -> List[Summary]:
    return [Summary(content=topic, count=count) for topic, count in topics_with_counts]

def parse_summary_json(response_text: str) -> List[Summary]:
    try:
        data = json.loads(response_text)
        return [Summary(content=item["content"], count=item["count"]) for item in data]
    except json.JSONDecodeError:
        print("❌ JSON 파싱 실패, fallback 실행")
        topics = extract_summary_topics(response_text)
        return build_summary(topics)

def analyze_reviews_with_ai(
    reviews: List[ReviewItem],
    department_name: str,
    top_k: int = 2
) -> Tuple[List[Summary], List[Summary], str]:

    positive_texts = [r.content for r in reviews if r.positive]
    negative_texts = [r.content for r in reviews if not r.positive]

    print(f"총 리뷰 개수: {len(reviews)}")
    print(f"긍정 리뷰 개수: {len(positive_texts)}")
    print(f"부정 리뷰 개수: {len(negative_texts)}")
    print("📌 긍정 리뷰 목록:")
    for i, text in enumerate(positive_texts, 1):
        print(f"{i}. {text}")
    print("\n📌 부정 리뷰 목록:")
    for i, text in enumerate(negative_texts, 1):
        print(f"{i}. {text}")
    print("\n----------------------------\n")

    # 요약 생성
    summary_prompt_template = load_prompt(summary_prompt_path)

    def generate_summary(texts: List[str], sentiment: str) -> List[Summary]:
        if not texts:
            return []
        review_list = "\n".join(f"- {t}" for t in texts)
        prompt = summary_prompt_template.format(
            sentiment=sentiment,
            top_k=top_k,
            review_list=review_list
        )
        response_text = call_gpt_with_prompt(prompt)
        return parse_summary_json(response_text)

    pos_summary = generate_summary(positive_texts, "긍정")
    neg_summary = generate_summary(negative_texts, "부정")

    # 리포트 생성
    report_prompt_template = load_prompt(report_prompt_path)
    pos_text = "\n".join([f"{i+1}. '{s.content}' ({s.count}개)" for i, s in enumerate(pos_summary)])
    neg_text = "\n".join([f"{i+1}. '{s.content}' ({s.count}개)" for i, s in enumerate(neg_summary)])

    report_prompt = report_prompt_template.format(
        positive_summary=pos_text,
        negative_summary=neg_text,
        department_name=department_name
    )

    report_text = call_gpt_with_prompt(report_prompt, max_tokens=500)

    return pos_summary, neg_summary, report_text
