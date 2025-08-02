from typing import List
from pydantic import BaseModel

class ReviewItem(BaseModel):
    content: str
    date: str
    score: str
    like: str

class DepartmentReviewResponse(BaseModel):
    department_name: str
    reviews: List[ReviewItem]
