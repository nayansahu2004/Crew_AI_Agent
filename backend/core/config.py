# File path: backend/core/config.py
"""
Centralized application settings.

Reads all environment variables ONCE, at process startup, into a single
typed object. Import `settings` (the module-level instance) everywhere
else in the app instead of calling os.getenv() directly.

Only values the backend genuinely cannot run without are required. The
rest are optional so a missing one doesn't stop the whole API booting.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Supabase Auth ---
    # Required: used to locate the project's public signing keys (JWKS)
    # for verifying access tokens.
    supabase_url: str
    # Not used by the backend today -- optional, kept for later features.
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    # Only needed if your Supabase project still signs tokens with the
    # legacy shared HS256 secret. Newer projects use asymmetric keys and
    # don't need this at all (see core/security.py).
    supabase_jwt_secret: str | None = None

    # --- MongoDB ---
    mongodb_uri: str
    mongodb_database: str = "crew_ai_agent"

    # --- AI providers ---
    # Optional: agents.py falls back to local Ollama when Gemini is
    # unavailable, so a missing Gemini key must not block startup.
    gemini_api_key: str | None = None
    serper_api_key: str
    firecrawl_api_key: str
    tavily_api_key: str
    ollama_base_url: str = "http://localhost:11434"

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS is a comma-separated string in .env; this splits
        it into the list FastAPI's CORSMiddleware expects."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so .env is only read/parsed once per process."""
    return Settings()


settings = get_settings()