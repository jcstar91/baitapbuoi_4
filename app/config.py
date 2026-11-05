import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL")
    ai_mode: str = os.getenv("AI_MODE")
    database_url: str = os.getenv("DATABASE_URL")
    ai_max_requests_per_hour: int = int(os.getenv("AI_MAX_REQUESTS_PER_HOUR"))
    cookie_secure: bool = os.getenv("COOKIE_SECURE") == "true"
    
def get_settings() -> Settings:
    return Settings()