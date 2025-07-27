FROM python:3.11.1

# 시간대 설정
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 시스템 폰트 설치
RUN apt-get update && \
    apt-get install -y fonts-nanum && \
    fc-cache -fv && \
    apt-get clean

# 작업 디렉토리 생성
WORKDIR /app

# requirements 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY ./app ./app

# 포트 노출
EXPOSE 8000

# 실행 명령
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
