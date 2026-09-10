import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


class Settings:
    # Auth
    secret_key: str = os.getenv("SECRET_KEY", "")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # AI / LLM (triage)
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    llm_model: str = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    # AI / Embeddings (duplicate detection)
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    embedding_base_url: str = os.getenv(
        "EMBEDDING_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
    )
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    duplicate_similarity_threshold: float = float(
        os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.85")
    )


settings = Settings()