from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # PostgreSQL 관련 설정
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # AWS 관련 설정
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_BUCKET_NAME: str
    AWS_REGION: str

    # OpenAI API 키
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    
    # JWT 관련 설정
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    class Config:
        env_file = ".env"

settings = Settings()
