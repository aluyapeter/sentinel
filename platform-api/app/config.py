from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    platform_database_url: str
    platform_secret_key: str
    platform_algorithm: str = "HS256"
    platform_admin_jwt_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings() #type: ignore