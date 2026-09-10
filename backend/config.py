"""
backend/config.py

Loads all application configuration from environment variables.
Uses pydantic-settings so every setting is typed and validated at startup.
The .env file is read automatically — secrets never appear in source code.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    database_url: str

    # --- Google Gemini ---
    gemini_api_key: str

    # --- AI Mock Mode ---
    # When True, the app returns realistic mock AI results without calling Gemini.
    # Set to False only when you want real Gemini API calls.
    ai_mock_mode: bool = True

    model_config = SettingsConfigDict(
        # Look for .env one level up from this file (i.e. support-crm/.env)
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # silently ignore unknown env vars
    )


# Single shared instance — import this everywhere instead of re-instantiating.
settings = Settings()
