from fastapi import FastAPI
from typing import Union
from app.routers import user_router, s3_router, analyze_router, department_router, main_router
from app.config.database import Base, engine

app = FastAPI()

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

# 라우터 등록
app.include_router(user_router.router)
app.include_router(s3_router.router) # 테스트를 위해 임시로 만들어서 나중에 삭제할 예정!! 
app.include_router(analyze_router.router)
app.include_router(department_router.router)
app.include_router(main_router.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}