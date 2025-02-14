from typing import Annotated

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi_discord import RateLimited, Unauthorized
from fastapi_discord.exceptions import ClientSessionNotInitialized
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware

import models
import asyncio
import uvicorn
from contextlib import asynccontextmanager

from routers import session, account, users, proposals, polls
from shared import discord, db, UserNotRegistered, config, get_current_user
from bot import bot

# noinspection PyShadowingNames,PyUnusedLocal
@asynccontextmanager
async def lifespan(app: FastAPI):
    if await db.elections.find_one({"current": True}) is None:
        voters = []
        async for user in db.users.find({"party": ObjectId("678cf02d79a12f76db9af7ae"), "inactive": False}):
            voters.append({"user": ObjectId(user["_id"]), "voted": False})
        await db.elections.insert_one({"current": True, "registered_voters": voters, "ballots": []})
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=config["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/election", response_model=models.ElectionModel ,dependencies=[Depends(discord.requires_authorization)])
async def get_election():
    election =  await db.elections.find_one({"current": True})
    voters = []
    for i in election["registered_voters"]:
        voters.append(await db.get_user({"_id": i["user"]}))
    return {"voters": voters, "votes_cast": len(election["ballots"])}

async def user_allowed_to_vote(current_user: Annotated[dict, Depends(get_current_user)]):
    election =  await db.elections.find_one({"current": True})
    user_found = False
    for i in election["registered_voters"]:
        if i["user"] == current_user["_id"]:
            user_found = True
            if i["voted"]:
                raise Exception()
    if not user_found:
        raise Exception
    return True


@app.get("/am_i_even_allowed_to_vote", response_model=models.VoterStatusModel, dependencies=[Depends(discord.requires_authorization)])
async def get_am_i_even_allowed_to_vote(current_user: Annotated[dict, Depends(get_current_user)]):
    election =  await db.elections.find_one({"current": True})
    user_found = False
    for i in election["registered_voters"]:
        if i["user"] == current_user["_id"]:
            user_found = True
            if i["voted"]:
                return {"allowed": False, "reason": "You have already voted."}
    if not user_found:
        return {"allowed": False, "reason": "You cannot vote because you registered after the election deadline."}
    return {"allowed": True, "reason": "You are registered to vote."}


@app.post("/election", dependencies=[Depends(user_allowed_to_vote), Depends(discord.requires_authorization)])
async def cast_ballot(ballot: models.Ballot, current_user: Annotated[dict, Depends(get_current_user)]):
    election =  await db.elections.find_one({"current": True})
    print(ballot)
    await db.elections.update_one({"_id": election["_id"]}, {"$set": {"registered_voters.$[elem].voted": True}}, array_filters=[{"elem.user": ObjectId(current_user["_id"])}])
    await db.elections.update_one({"_id": election["_id"]}, {"$push": {"ballots": ballot.model_dump()}})
    print(election)
    return ""

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
    return JSONResponse(models.ErrorModel(error="UserNotRegistered", message="You must finish registration to access this resource.").model_dump(), status_code=401)
