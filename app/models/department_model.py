from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.config.database import Base

class Department(Base):
    __tablename__ = "department"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)

    review_departments = relationship("ReviewDepartment", back_populates="department")
