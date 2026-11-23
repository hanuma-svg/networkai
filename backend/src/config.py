from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """NetworkAI Backend application configuration."""
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    GEMINI_API_KEY: str = ""
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"
    INNGEST_EVENT_KEY: Optional[str] = None
    INNGEST_SIGNING_KEY: Optional[str] = None

    # LinkedIn Official Posts API credentials (optional / can be passed in request)
    LINKEDIN_ACCESS_TOKEN: Optional[str] = None
    LINKEDIN_AUTHOR_URN: Optional[str] = None

    PORT: int = 8000
    ENVIRONMENT: str = "development"

    @property
    def clean_supabase_url(self) -> str:
        """Strips /rest/v1 or trailing slashes for the Supabase client which requires base URL."""
        url = self.SUPABASE_URL.strip()
        if not url:
            return ""
        if "/rest/v1" in url:
            url = url.split("/rest/v1")[0]
        return url.rstrip("/")


settings = Settings()
