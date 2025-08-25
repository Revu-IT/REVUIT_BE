from typing import List
from pydantic import BaseModel

class ReviewItem(BaseModel):
    content: str
    date: str
    score: float | None
    like: int
    positive: bool

class DepartmentReviewResponse(BaseModel):
    department_name: str
    reviews: List[ReviewItem]

class Summary(BaseModel):
    content: str
    count: int

class DepartmentSummaryResponse(BaseModel):
    department_name: str
    positive_opinions: List[Summary]
    negative_opinions: List[Summary]
    reports: str

class CompanyQuarterSummaryResponse(BaseModel):
    company: str
    positive: bool
    summary: str
