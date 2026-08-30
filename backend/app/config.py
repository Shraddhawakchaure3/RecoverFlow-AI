"""
RecoverFlow AI - Application Configuration
Loads and validates all environment variables using Pydantic Settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "dev-secret-key-change-in-production"

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017/recoverflow"

    # AI Provider
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"

    # Policy defaults
    max_retries: int = 2
    max_recovery_actions: int = 3
    min_recovery_score: float = 0.40
    max_transaction_amount: int = 1_000_000

    # CORS
    frontend_url: str = "http://localhost:5173"

    @property
    def is_razorpay_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def is_ai_configured(self) -> bool:
        return bool(self.ai_api_key)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
