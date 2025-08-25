from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from app.services.s3_service import upload_to_s3, list_all_s3_csv_files

router = APIRouter(prefix="/s3", tags=["s3"])

# 테스트를 위한 임시 라우터 
@router.post(
    "/upload/",
    summary="S3 파일 업로드 API",
    description="""
    S3 파일 업로드를 위한 테스트용 API입니다.
    """
)
async def upload_file(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        bucket_name = "hanium-reviewit"
        file_name = file.filename
        folder_name = "11st" # 임시 ! 
        
        # S3에 업로드
        upload_result = upload_to_s3(bucket_name, folder_name, file_name, file_content)
        return JSONResponse(content={"message": upload_result})
    
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)

@router.get(
    "/list",
    summary="S3 내 모든 파일 목록 조회 API",
    description="""
    S3 버킷 내 모든 파일 목록을 조회합니다.
    """
)
def list_all_csv_files():
    return {"files": list_all_s3_csv_files()}