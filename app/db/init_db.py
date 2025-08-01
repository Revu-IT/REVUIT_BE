# 실행: python app/crud/init_db.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy.orm import Session
from app.config.database import SessionLocal, Base, engine
from app.models.user_model import User
from app.models.company_model import Company
from app.models.department_model import Department

def init_company_data():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # 회사 생성
    company_names = ["쿠팡", "알리", "G마켓", "11번가", "테무"]
    for idx, name in enumerate(company_names, start=1):
        if not db.query(Company).filter(Company.id == idx).first():
            db.add(Company(id=idx, name=name))

    # 부서 생성
    departments = [
        (1, "고객 서비스팀 (CS)"),
        (2, "물류 운영팀 (Logistics)"),
        (3, "상품 기획/운영팀 (MD)"),
        (4, "전략 기획/PM팀"),
        (5, "기술개발팀 (Tech/Dev)"),
        (6, "마케팅팀 (Marketing)"),
        (7, "재무/결제팀 (Finance)"),
        (8, "법무/컴플라이언스팀 (Legal)"),
        (9, "파트너/판매자 지원팀"),
        (10, "기타"),
    ]
    for dept_id, dept_name in departments:
        if not db.query(Department).filter(Department.id == dept_id).first():
            db.add(Department(id=dept_id, name=dept_name, description=dept_name))

    db.commit()

    db.close()

if __name__ == "__main__":
    init_company_data()
