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

from pydantic import Field
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

    # --- Search ---
    # Serper (https://serper.dev) gives the pipeline Google search results. It
    # is the only outside service the search pipeline uses.
    serper_api_key: str
    # How many searches one run may make (each costs one Serper credit), how
    # many creators to keep, and whether to save the raw search results to
    # backend/outputs/search_debug.jsonl (handy while tuning).
    pipeline_max_queries: int = Field(default=8, ge=1, le=20)
    pipeline_max_creators: int = Field(default=15, ge=1, le=50)
    pipeline_debug_dump: bool = False

    # --- Gmail (Google OAuth) ---
    # All three of google_client_id, google_client_secret and
    # token_encryption_key must be set for Gmail to be available; if any is
    # missing the app still runs, the Gmail features just report "not set
    # up". See `gmail_configured`.
    google_client_id: str | None = None
    google_client_secret: str | None = None
    # Must match an "Authorized redirect URI" on the Google OAuth client
    # EXACTLY (scheme, host, port, path).
    google_redirect_uri: str = "http://localhost:8000/api/gmail/callback"
    # Where the browser is sent after the Google consent screen.
    frontend_url: str = "http://localhost:5173"
    # Fernet key(s) used to encrypt Gmail refresh tokens at rest, and to
    # sign the OAuth `state` value. Comma-separate several keys to rotate:
    # the first encrypts, all of them can decrypt. Generate one with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    token_encryption_key: str | None = None
    # Safety cap on emails one user can send through the app per rolling
    # 24 hours (Gmail itself limits ~500/day for personal accounts).
    gmail_daily_send_limit: int = 100

    # --- Free searches ---
    # How many pipeline runs ("searches") a NEW account gets for free. Every
    # run uses one, including re-runs; a run that fails is refunded. Accounts
    # created before this existed have no counter and stay unlimited. Keep
    # the frontend's VITE_FREE_SEARCHES in step with this so the site copy
    # matches.
    free_runs_for_new_users: int = 2

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

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

    @property
    def gmail_configured(self) -> bool:
        return bool(
            self.google_client_id
            and self.google_client_secret
            and self.token_encryption_key
        )


@lru_cache
def get_settings() -> Settings:
    """Cached so .env is only read/parsed once per process."""
    return Settings()


settings = get_settings()