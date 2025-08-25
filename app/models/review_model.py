from sqlalchemy import Column, Integer, Text, Boolean, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from app.config.database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    content = Column(Text, nullable=True)
    cleaned_text = Column(Text, nullable=True)
    date = Column(TIMESTAMP, nullable=False)
    likes = Column(Integer, default=0)
    positive = Column(Boolean, default=True)
    score = Column(Numeric, nullable=True)

    company = relationship("Company", back_populates="reviews")
    review_departments = relationship("ReviewDepartment", back_populates="review")

class ReviewDepartment(Base):
    __tablename__ = "review_department"

    review_id = Column(Integer, ForeignKey("reviews.id"), primary_key=True)
    department_id = Column(Integer, ForeignKey("department.id"), primary_key=True)

    review = relationship("Review", back_populates="review_departments")
    department = relationship("Department", back_populates="review_departments")