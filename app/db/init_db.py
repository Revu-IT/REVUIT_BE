# 실행: python app/crud/init_db.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy.orm import Session
from app.config.database import SessionLocal, Base, engine
from app.models.user_model import Company, User
def init_company_data():
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()

    company_names = ["쿠팡", "알리", "G마켓", "11번가", "테무"]
    
    for idx, name in enumerate(company_names, start=1):
        if not db.query(Company).filter(Company.id == idx).first():
            db.add(Company(id=idx, name=name))
    db.commit()
    db.close()

if __name__ == "__main__":
    init_company_data()
