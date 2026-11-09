from typing import Literal

from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginIn(Strict):
    email: str
    password: str


class RefreshIn(Strict):
    refresh_token: str


class LanguageIn(Strict):
    language: Literal["en", "hi"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: str
    role: str
    institution_id: str | None
    language: str
