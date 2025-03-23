from fastapi import APIRouter
import models
from shared import discord

router = APIRouter()


@router.get("/", response_model=models.ServerInfoModel)
async def server_info():
    return {"login_url": discord.oauth_login_url}


@router.get("/callback", response_model=models.AuthCallbackModel)
async def callback(code: str):
    token, refresh_token = await discord.get_access_token(code)
    return {"access_token": token, "refresh_token": refresh_token}
