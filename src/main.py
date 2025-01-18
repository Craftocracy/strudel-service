from typing import Annotated

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi_discord import RateLimited, Unauthorized
from fastapi_discord.exceptions import ClientSessionNotInitialized
import datetime
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

import models

from contextlib import asynccontextmanager

from routers import session, account, users
from shared import discord, db, UserNotRegistered, config, get_current_user


# noinspection PyShadowingNames,PyUnusedLocal
@asynccontextmanager
async def lifespan(app: FastAPI):
    await discord.init()
    yield

app = FastAPI(swagger_ui_parameters={"persistAuthorization": True}, lifespan=lifespan)
app.include_router(session.router)
app.include_router(account.router)
app.include_router(users.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=config["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/election", response_model=models.ElectionModel)
async def get_election():
    election =  await db.elections.find_one()
    voters = []
    for i in election["registered_voters"]:
        voters.append(await db.get_user(i["user"]))
    return {"voters": voters, "votes_cast": len(election["ballots"])}

async def user_allowed_to_vote(current_user: Annotated[dict, Depends(get_current_user)]):
    election =  await db.elections.find_one()
    user_found = False
    for i in election["registered_voters"]:
        if i["user"] == current_user["_id"]:
            user_found = True
            if i["voted"]:
                raise Exception()
    if not user_found:
        raise Exception
    return True


@app.get("/am_i_even_allowed_to_vote", response_model=models.VoterStatusModel)
async def get_am_i_even_allowed_to_vote(current_user: Annotated[dict, Depends(get_current_user)]):
    election =  await db.elections.find_one()
    user_found = False
    for i in election["registered_voters"]:
        if i["user"] == current_user["_id"]:
            user_found = True
            if i["voted"]:
                return {"allowed": False, "reason": "You have already voted."}
    if not user_found:
        return {"allowed": False, "reason": "You cannot vote because you registered after the election deadline."}
    return {"allowed": True, "reason": "You are registered to vote."}


@app.post("/election", dependencies=[Depends(user_allowed_to_vote)])
async def cast_ballot(ballot: models.Ballot, current_user: Annotated[dict, Depends(get_current_user)]):
    election =  await db.elections.find_one()
    print(ballot)
    await db.elections.update_one({"_id": election["_id"]}, {"$set": {"registered_voters.$[elem].voted": True}}, array_filters=[{"elem.user": ObjectId(current_user["_id"])}])
    await db.elections.update_one({"_id": election["_id"]}, {"$push": {"ballots": ballot.model_dump()}})
    print(election)
    return ""

@app.get("/parties/", response_model=models.PartyCollection)
async def list_parties():
    return models.PartyCollection(parties=await db.query_parties())

@app.get("/parties/{party_id}", response_model=models.PartyModel)
async def get_party(party_id: str):
    return await db.get_party(ObjectId(party_id))


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
