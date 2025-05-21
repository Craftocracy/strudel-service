import asyncio
from contextlib import asynccontextmanager

from bson import ObjectId
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_discord import RateLimited, Unauthorized
from fastapi_discord.exceptions import ClientSessionNotInitialized

import models
from bot import bot
from routers import session, account, users, proposals, polls, elections, polls_v2
from shared import discord, db, UserNotRegistered, config


# noinspection PyShadowingNames,PyUnusedLocal
@asynccontextmanager
async def lifespan(app: FastAPI):
    await discord.init()

    loop = asyncio.get_event_loop()
    bot_task = loop.create_task(bot.client.start(config["discord"]["bot_token"]))
    yield


app = FastAPI(swagger_ui_parameters={"persistAuthorization": True}, lifespan=lifespan)
app.include_router(session.router)
app.include_router(account.router)
app.include_router(users.router)
app.include_router(proposals.router)
app.include_router(polls.router)
app.include_router(elections.router)
app.include_router(polls_v2.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/parties/", response_model=models.PartyCollection)
async def list_parties():
    return models.PartyCollection(parties=await db.query_parties({}))


@app.get("/parties/{party_id}", response_model=models.PartyModel)
async def get_party(party_id: str):
    return await db.get_party({"_id": ObjectId(party_id)})


@app.exception_handler(Unauthorized)
async def unauthorized_error_handler(_, __):
    return JSONResponse({"error": "Unauthorized"}, status_code=403)


@app.exception_handler(RateLimited)
async def rate_limit_error_handler(_, e: RateLimited):
    return JSONResponse(
        {"error": "RateLimited", "retry": e.retry_after, "message": e.message},
        status_code=429,
    )


@app.exception_handler(ClientSessionNotInitialized)
async def client_session_error_handler(_, e: ClientSessionNotInitialized):
    print(e)
    return JSONResponse({"error": "Internal Error"}, status_code=500)


@app.exception_handler(UserNotRegistered)
async def user_not_registered_error_handler(_, e: UserNotRegistered):
    print(e)
    return JSONResponse(models.ErrorModel(error="UserNotRegistered",
                                          message="You must finish registration to access this resource.").model_dump(),
                        status_code=401)
