from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str
    ALEMBIC_DATABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWKS_URL: str
    SUPABASE_URL: str
    GEMINI_MODEL:str
    STORAGE_BUCKET:str
    ENVIRONMENT:str
    MAX_UPLOAD_SIZE_MB:int
    SUPABASE_JWT_SECRET: str    

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    class Config:
        env_file = ".env"

settings = Settings()