from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class AppSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_enabled: bool | None = None
    maintenance_mode: bool | None = None
    force_update: bool | None = None
    minimum_version: str | None = Field(default=None, min_length=1, max_length=30)
    update_message: str | None = Field(default=None, max_length=1000)


class PremiumGrantRequest(BaseModel):
    plan: Literal["monthly", "yearly", "lifetime"]
    reason: str = Field(default="Manual admin grant", max_length=500)
