from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from app.services.s3_service import upload_to_s3 

router = APIRouter(prefix="/s3", tags=["s3"])

# 테스트를 위한 임시 라우터 
@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        bucket_name = "hanium-reviewit"
        file_name = file.filename
        folder_name = "coupang" # 임시 ! 
        
        # S3에 업로드
        upload_result = upload_to_s3(bucket_name, folder_name, file_name, file_content)
        return JSONResponse(content={"message": upload_result})
    
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)