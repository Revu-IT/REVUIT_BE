from fastapi import APIRouter, HTTPException, Depends
from app.services.analyze_service import generate_wordcloud_and_upload_from_csv
from app.services.user_service import get_current_user
from app.models.user_model import User

router = APIRouter(prefix="/analyze", tags=["analyze"])

@router.get("/wordcloud/{sentiment}")
def get_wordcloud(
    sentiment: str,
    current_user: User = Depends(get_current_user)
):
    if sentiment not in ["positive", "negative"]:
        raise HTTPException(status_code=400, detail="sentiment는 'positive' 또는 'negative'여야 합니다.")

    # 영어 이름 매핑 
    company_map = {
        1: "coupang", 2: "aliexpress", 3: "gmarket", 4: "11st", 5: "temu"
    }
    company_name = company_map.get(current_user.company_id)
    if not company_name:
        raise HTTPException(status_code=400, detail="유효하지 않은 회사 ID")

    # csv 저장 경로 지정 
    s3_key = f"positive/{company_name}.csv"  
    try:
        image_url = generate_wordcloud_and_upload_from_csv(s3_key, sentiment, company_name)
        return {"image_url": image_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
