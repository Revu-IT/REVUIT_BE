from sqlalchemy.orm import Session
from app.models.company_model import Company

def get_company_by_id(db: Session, company_id: int):
    return db.query(Company).filter(Company.id == company_id).first()
