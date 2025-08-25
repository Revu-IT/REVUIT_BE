from typing import List
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.department_model import Department
from app.models.review_model import Review, ReviewDepartment
from app.schemas.review_schema import DepartmentReviewResponse, ReviewItem, DepartmentSummaryResponse
from app.config.errors import ErrorMessages
from app.utils.ai_util import analyze_reviews_with_ai

def get_department_name_by_id(db: Session, department_id: int) -> str:
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise ValueError(ErrorMessages.INVALID_DEPARTMENT_ID)
    return department.name

def get_department_reviews(db: Session, department_id: int, company_id: int) -> DepartmentReviewResponse:
    department_name = get_department_name_by_id(db, department_id)

    reviews_query = (
        db.query(Review)
        .join(ReviewDepartment)
        .filter(
            ReviewDepartment.department_id == department_id,
            Review.company_id == company_id
        )
        .all()
    )

    if not reviews_query:
        raise ValueError(f"'{department_name}' 부서에 리뷰가 없습니다.")

    results: List[ReviewItem] = []

    for r in reviews_query:
        try:
            results.append(
                ReviewItem(
                    content=r.content or "",
                    date=r.date.strftime("%Y-%m-%d %H:%M:%S"),
                    score=float(r.score) if r.score is not None else None,
                    like=int(r.likes or 0),
                    positive=r.positive,
                )
            )
        except Exception:
            continue

    return DepartmentReviewResponse(
        department_name=department_name,
        reviews=results
    )

def analyze_department_review(db: Session, department_id: int, company_id: int) -> DepartmentSummaryResponse:
    department_review_response = get_department_reviews(db, department_id, company_id)
    reviews = department_review_response.reviews

    three_months_ago = datetime.now() - timedelta(days=90)
    filtered_reviews = [
        r for r in reviews
        if datetime.strptime(r.date, "%Y-%m-%d %H:%M:%S") >= three_months_ago
    ]

    positive_opinions, negative_opinions, reports = analyze_reviews_with_ai(
        filtered_reviews, department_review_response.department_name
    )

    return DepartmentSummaryResponse(
        department_name=department_review_response.department_name,
        positive_opinions=positive_opinions,
        negative_opinions=negative_opinions,
        reports=reports
    )