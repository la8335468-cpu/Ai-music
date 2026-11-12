import json
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ABHISHEK MUSIC"
    environment: str = "production"
    database_url: str
    firebase_project_id: str
    firebase_service_account_json: str
    admin_uids: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def admins(self) -> set[str]:
        return {x.strip() for x in self.admin_uids.split(",") if x.strip()}

    @property
    def firebase_credentials(self) -> dict:
        try:
            return json.loads(self.firebase_service_account_json)
        except json.JSONDecodeError as exc:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON must contain valid JSON") from exc


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
