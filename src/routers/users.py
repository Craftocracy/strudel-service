from typing import Optional, Annotated

from bson import ObjectId
from fastapi import APIRouter, Query
from pydantic import BaseModel, BeforeValidator

import models
from shared import db

router = APIRouter(prefix="/users", tags=["Users"])


def none_from_str(value: str) -> str | None:
    if value == "null":
        return None
    return value


class FilterParams(BaseModel):
    party: Annotated[Optional[str], BeforeValidator(none_from_str)] = None
    inactive: Optional[bool] = None


@router.get("/", response_model=models.UserCollection)
async def list_users(filter_query: Annotated[FilterParams, Query()]):
    query = filter_query.model_dump(exclude_unset=True)
    if query.get("party"):
        query["party"] = ObjectId(query.pop("party"))
    return models.UserCollection(users=await db.query_users(query))


@router.get("/{user_id}", response_model=models.UserModel)
async def get_user(user_id: str):
    return await db.get_user({"_id": ObjectId(user_id)})
