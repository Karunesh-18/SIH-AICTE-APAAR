from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-any-shared-environment"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./apaar.db"
    jwt_secret: str = DEFAULT_JWT_SECRET
    access_minutes: int = 30
    refresh_days: int = 7
    refresh_grace_seconds: int = 10  # a just-rotated refresh token is accepted once more (tab race)
    demo_mode: bool = True
    scheduler: bool = False  # SCHEDULER=1 starts the window cycle even in demo mode
    scheduler_minutes: int = 15
    login_max_attempts: int = 10
    bcrypt_rounds: int = 12
    # Verification tokens (Ed25519). The key file is generated on first run and never committed.
    verify_key_path: str = "keys/verify_ed25519.pem"
    verify_token_days: int = 7
    certificate_token_days: int = 1825  # printed on paper, so long-lived (5 years)
    verify_issuer: str = "waymark-apaar-hub"
    public_base_url: str = "http://localhost:3000"  # what the QR code opens: {base}/verify/{token}
    verify_max_refusals: int = 30  # refused requests per verifier per 5 minutes
    register_max_per_hour: int = 5  # verifier registrations per client address
    check_max_per_minute: int = 120  # public token checks per client address
    # Email: "console" (default, logs only, no network) or "smtp".
    email_backend: Literal["console", "smtp"] = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_use_tls: bool = True  # STARTTLS; port 465 always uses implicit SSL
    email_from: str = ""
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @model_validator(mode="after")
    def _smtp_needs_host_and_sender(self):
        if self.email_backend == "smtp" and not (self.smtp_host and self.email_from):
            raise ValueError("EMAIL_BACKEND=smtp needs SMTP_HOST and EMAIL_FROM")
        return self

    @model_validator(mode="after")
    def _real_secret_outside_demo(self):
        # A known default secret would let anyone forge tokens.
        if not self.demo_mode and (self.jwt_secret == DEFAULT_JWT_SECRET
                                   or len(self.jwt_secret) < 32):
            raise ValueError("Set JWT_SECRET to a random value of 32+ characters "
                             "when DEMO_MODE is off")
        return self


settings = Settings()
