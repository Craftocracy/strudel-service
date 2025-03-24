from fastapi import Depends, Request
from fastapi_discord import DiscordOAuthClient, User, Unauthorized
import yaml
import requests
import os
from typing import Annotated
from database import Database
from urllib.parse import urljoin

with open(os.path.join(os.environ["DATADIR"], "config.yml"), 'r') as file:
    config: dict = yaml.safe_load(file)

discord: DiscordOAuthClient = DiscordOAuthClient(
    config["discord"]["client_id"], config["discord"]["client_secret"], config["discord"]["redirect_url"], ["identify"]
)

db: Database = Database(config["database"]["strudel"]["mongo_uri"])


class UserNotRegistered(Exception):
    """An Exception raised when user is authorized, but not registered."""


class RegistrationProhibited(Exception):
    """An Exception raised when the user is not allowed to register."""


async def get_current_user(dc_user: Annotated[User, Depends(discord.user)]):
    try:
        return await db.get_user({"dc_uuid": dc_user.id})
    except KeyError:
        return None


async def maybe_get_current_user(request: Request):
    try:
        return await get_current_user(dc_user=await discord.user(request))
    except (KeyError, Unauthorized):
        return None


async def requires_registration(current_user: Annotated[dict, Depends(get_current_user)]):
    if current_user is not None:
        return True
    else:
        raise UserNotRegistered


async def registration_allowed(current_user: Annotated[dict, Depends(get_current_user)]):
    if current_user is None:
        return True
    else:
        raise RegistrationProhibited


async def get_minecraft_user(user: Annotated[User, Depends(discord.user)]):
    linking_db = requests.get(config["database"]["discord_linking"]["url"]).json()

    for player in linking_db:
        if player["discordID"] == user.id:
            return player["mcPlayerUUID"]
    raise RegistrationProhibited


def webapp_page(path: str):
    return urljoin(config["web_base"], path)


print("shared called")
