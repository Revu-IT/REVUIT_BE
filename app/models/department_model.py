from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base

class Department(Base):
    __tablename__ = "department"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), nullable=False)
    description = Column(String(225), nullable=False)
