from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.config.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    users = relationship("User", back_populates="company")
    reviews = relationship("Review", back_populates="company")