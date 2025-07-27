from fastapi import HTTPException
from app.models.user_model import User

def get_s3_csv_key(user: User) -> str:
    company_map = {
        1: "coupang", 2: "aliexpress", 3: "gmarket", 4: "11st", 5: "temu"
    }
    company_name = company_map.get(user.company_id)
    if not company_name:
        raise HTTPException(status_code=400, detail="유효하지 않은 회사 ID")

    return f"positive/{company_name}.csv", company_name
