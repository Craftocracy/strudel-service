from fastapi import Depends
from fastapi_discord import DiscordOAuthClient, User
import yaml
import aiomysql
import os
from typing import Annotated
from database import Database

with open(os.path.join(os.environ["DATADIR"], "config.yml"), 'r') as file:
    config: dict = yaml.safe_load(file)

discord: DiscordOAuthClient = DiscordOAuthClient(
    config["discord"]["client_id"], config["discord"]["client_secret"], config["discord"]["redirect_url"], ["identify"]
)

db: Database = Database(config["database"]["strudel"]["mongo_uri"])

discord_linking_db: aiomysql.Pool

async def init_linking_db():
    global discord_linking_db
    discord_linking_db = await aiomysql.create_pool(**config["database"]["discord_linking"])


class UserNotRegistered(Exception):
    """An Exception raised when user is authorized, but not registered."""

class RegistrationProhibited(Exception):
    """An Exception raised when the user is not allowed to register."""

async def get_current_user(dc_user: Annotated[User, Depends(discord.user)]):
    return await db.get_user({"dc_uuid": dc_user.id})


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
    async with discord_linking_db.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT mcuuid FROM PlayerLinks WHERE id = %s", user.id)
            response = await cursor.fetchone()
            return response[0]


print("shared called")