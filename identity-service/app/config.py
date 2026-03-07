from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    identity_database_url: str
    identity_secret_key: str
    identity_algorithm: str = "HS256"
    identity_user_jwt_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings() #type: ignore