from bson import ObjectId
from fastapi import APIRouter
from shared import db
import models

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=models.UserCollection)
async def list_users():
    return models.UserCollection(users=await db.query_users({"inactive": False}))

@router.get("/{user_id}", response_model=models.UserModel)
async def get_user(user_id: str):
    return await db.get_user({"_id": ObjectId(user_id)})
