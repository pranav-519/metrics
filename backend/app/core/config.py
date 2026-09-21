import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Legal Metrology Packaged Commodities Compliance Scanner"
    PROJECT_SLUG: str = "metricheck"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Database
    # Default to SQLite for seamless local hackathon run, PostgreSQL supported seamlessly via DATABASE_URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./legal_metrology.db")
    
    # Upload storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE_MB: int = 15
    ALLOWED_IMAGE_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png", ".webp"]
    
    # Rules versioning
    DEFAULT_LEGAL_FRAMEWORK: str = "Legal Metrology (Packaged Commodities) Rules, 2011"
    DEFAULT_RULE_VERSION: str = "2024.1"

    # OCR Pipeline Configuration
    OCR_ENGINE: str = os.getenv("OCR_ENGINE", "paddleocr")
    OCR_MODEL: str = os.getenv("OCR_MODEL", "PP-OCRv6")
    OCR_DEVICE: str = os.getenv("OCR_DEVICE", "cpu")
    OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "en")
    OCR_CONFIDENCE_THRESHOLD: float = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.50"))
    OCR_ENABLE_FALLBACK: bool = os.getenv("OCR_ENABLE_FALLBACK", "true").lower() in ("true", "1", "yes")
    OCR_MAX_ATTEMPTS: int = int(os.getenv("OCR_MAX_ATTEMPTS", "2"))
    OCR_TIMEOUT: int = int(os.getenv("OCR_TIMEOUT", "30"))
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)

    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()
