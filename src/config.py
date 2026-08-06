import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "EFL Global IDP API"
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/efl_idp")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Azure Credentials (Placeholders or Env Vars)
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
    
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")

    # Storage Paths
    SCANNER_INPUT_DIR: Path = BASE_DIR / "data" / "scanner_input"
    EFL_DOCUMENTS_DIR: Path = BASE_DIR / "data" / "efl_documents"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

# Ensure directories exist
settings.SCANNER_INPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.EFL_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
