from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./apaar.db"
    jwt_secret: str = "change-me-in-any-shared-environment"
    access_minutes: int = 30
    refresh_days: int = 7
    demo_mode: bool = True
    login_max_attempts: int = 10
    bcrypt_rounds: int = 12


settings = Settings()
