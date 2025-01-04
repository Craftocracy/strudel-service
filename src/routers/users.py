import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends
from shared import db
import models

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=models.UserCollection)
async def list_users():
    users = await db.users.find({}).to_list()
    for i in users:
        if ObjectId(i["_id"]).generation_time < datetime.datetime.fromtimestamp(1735606800, datetime.UTC):
            print(i["name"])
    return models.UserCollection(users=await db.query_users())

@router.get("/{user_id}", response_model=models.UserModel)
async def get_user(user_id: str):
    return await db.get_user(ObjectId(user_id))