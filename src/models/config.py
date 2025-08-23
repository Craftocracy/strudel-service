from typing import List

from pydantic import BaseModel


class DatabaseConfigModel(BaseModel):
    mongo: str
    discord_integration: str
    # plan: str


class DiscordConfigModel(BaseModel):
    guild: int
    notifications_channel: int
    token: str
    client_id: str
    client_secret: str
    auth_redirect: str


class WebserverConfigModel(BaseModel):
    cors_origins: List[str]
    frontend_base: str


class ConfigModel(BaseModel):
    database: DatabaseConfigModel
    discord: DiscordConfigModel
    webserver: WebserverConfigModel
    schema_ver: int
