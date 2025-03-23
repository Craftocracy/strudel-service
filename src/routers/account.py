from fastapi import APIRouter, Depends, BackgroundTasks
from bot import bot
from shared import discord, get_current_user, requires_registration, registration_allowed, db, get_minecraft_user, \
    webapp_page
from fastapi_discord import User
from models import RegistrationModel, UserModel, UserAccountModel
from typing import Annotated

router = APIRouter(dependencies=[Depends(discord.requires_authorization)], prefix="/account", tags=["Account"])


@router.get("/", dependencies=[Depends(requires_registration)], response_model=UserAccountModel)
async def get_account(current_user: Annotated[UserModel, Depends(get_current_user)]):
    return current_user


@router.post("/", dependencies=[Depends(registration_allowed)], response_model=UserAccountModel, status_code=201)
async def register_user(minecraft_user: Annotated[str, Depends(get_minecraft_user)],
                        user: Annotated[User, Depends(discord.user)], registration: RegistrationModel,
                        background_tasks: BackgroundTasks):
    insert = await db.users.insert_one({
        "dc_uuid": user.id,
        "mc_uuid": minecraft_user,
        "name": registration.name,
        "pronouns": registration.pronouns,
        "inactive": False,
        "party": None
    })
    background_tasks.add_task(bot.notify, message=f"New user registered: <@{user.id}>\n"
                                                  f"<{webapp_page(f"/users/{str(insert.inserted_id)}")}>")
    return await db.get_user({"dc_uuid": user.id})
