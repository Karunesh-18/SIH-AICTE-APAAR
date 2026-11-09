from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-any-shared-environment"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./apaar.db"
    jwt_secret: str = DEFAULT_JWT_SECRET
    access_minutes: int = 30
    refresh_days: int = 7
    demo_mode: bool = True
    scheduler: bool = False  # SCHEDULER=1 starts the window cycle even in demo mode
    scheduler_minutes: int = 15
    login_max_attempts: int = 10
    bcrypt_rounds: int = 12
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @model_validator(mode="after")
    def _real_secret_outside_demo(self):
        # A known default secret would let anyone forge tokens.
        if not self.demo_mode and (self.jwt_secret == DEFAULT_JWT_SECRET
                                   or len(self.jwt_secret) < 32):
            raise ValueError("Set JWT_SECRET to a random value of 32+ characters "
                             "when DEMO_MODE is off")
        return self


settings = Settings()
