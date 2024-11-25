from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi_discord import RateLimited, Unauthorized
from fastapi_discord.exceptions import ClientSessionNotInitialized

from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
import models

from contextlib import asynccontextmanager

from routers import session, account
from shared import discord, db, UserNotRegistered, config, init_linking_db


# noinspection PyShadowingNames,PyUnusedLocal
@asynccontextmanager
async def lifespan(app: FastAPI):
    await discord.init()
    await init_linking_db()
    yield

app = FastAPI(swagger_ui_parameters={"persistAuthorization": True}, lifespan=lifespan)
app.include_router(session.router)
app.include_router(account.router)



@app.get("/parties/", response_model=models.PartyCollection)
async def list_parties():
    return models.PartyCollection(parties=await db.query_parties())

@app.get("/parties/{party_id}", response_model=models.PartyModel)
async def get_party(party_id: str):
    return await db.get_party(ObjectId(party_id))
@app.get("/users/", response_model=models.UserCollection)
async def list_users():
    return models.UserCollection(users=await db.query_users())

@app.get("/users/{user_id}", response_model=models.UserModel)
async def get_user(user_id: str):
    return await db.get_user(ObjectId(user_id))


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
