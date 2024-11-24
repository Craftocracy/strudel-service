from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_discord import User
import models
from models import SessionInfoModel
from shared import discord, get_current_user, requires_registration


router = APIRouter()

@router.get("/", response_model=models.ServerInfoModel)
async def server_info():
    return {"login_url": discord.oauth_login_url}


@router.get("/callback", response_model=models.AuthCallbackModel)
async def callback(code: str):
    token, refresh_token = await discord.get_access_token(code)
    return {"access_token": token, "refresh_token": refresh_token}
