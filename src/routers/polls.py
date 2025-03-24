from typing import Annotated, List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, BackgroundTasks, Query
from pydantic import BaseModel

from bot import bot
from shared import db, discord, get_current_user, maybe_get_current_user, webapp_page
import models
import math
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/polls", tags=["Polls"])


def thresholds(total: int) -> List[int]:
    if total % 2 == 0:
        pass_threshold = int(total / 2) + 1
        fail_threshold = int(total / 2)
    else:
        pass_threshold = fail_threshold = math.ceil(total / 2)
    return [pass_threshold, fail_threshold]


class FilterParams(BaseModel):
    poll_open: Optional[bool] = None
    i_voted: Optional[bool] = None
    i_can_vote: Optional[bool] = None


@router.get("/", response_model=models.PollCollection)
async def get_polls(filter_query: Annotated[FilterParams, Query()],
                    current_user: Annotated[dict, Depends(maybe_get_current_user)]):
    query = filter_query.model_dump(exclude_unset=True)
    if "poll_open" in query:
        if filter_query.poll_open:
            operator = "$gt"
        else:
            operator = "$lte"
        query["closes"] = {operator: datetime.now(timezone.utc)}
        query.pop("poll_open")
    if "i_can_vote" in query:
        if current_user is not None:
            match = {"$elemMatch": {"user": current_user["_id"]}}
            if filter_query.i_can_vote:
                query["voters"] = match
            else:
                query["voters"] = {"$not": match}
        query.pop("i_can_vote")
    if "i_voted" in query:
        if current_user is not None:
            if filter_query.i_voted:
                choice = {"$ne": None}
            else:
                choice = None
            query["voters"] = {"$elemMatch": {
                "user": current_user["_id"],
                "choice": choice
            }}
        query.pop("i_voted")
    search = await db.query_polls(query)
    return {"polls": search}


@router.get("/{poll_id}", response_model=models.PollModel)
async def get_poll(poll_id: str):
    return await db.get_poll({"_id": ObjectId(poll_id)})


async def after_vote(poll_id: str):
    poll = await db.get_poll({"_id": ObjectId(poll_id)}, respect_secrets=False)
    if poll["secret"] is True:
        current_votes = sum(choice["votes"] for choice in poll["choices"])
        if current_votes != poll["total_voters"]:
            return
    if poll["can_change_vote"] is False:
        return
    goal_name = ""
    if poll["choices"][0]["votes"] >= poll["thresholds"][0]:
        goal_name = "PASSED"
    if poll["choices"][1]["votes"] >= poll["thresholds"][1]:
        goal_name = "FAILED"
    if goal_name != "":
        await db.polls.update_one({"_id": ObjectId(poll_id)}, {"$set": {"can_change_vote": False}})
        await bot.notify(f"{goal_name}: {poll["title"]}\n"
                         f"{webapp_page(f"/polls/{poll_id}")}")


@router.post("/{poll_id}/vote", dependencies=[Depends(discord.requires_authorization)])
async def poll_vote(poll_id: str, current_user: Annotated[dict, Depends(get_current_user)],
                    choice: models.PostPollVoteModel, background_tasks: BackgroundTasks):
    # FIX THIS SHIT!!
    pipeline = [
        # Unwind the voters array
        {"$unwind": "$voters"},
        # Match the specific user
        {"$match": {"_id": ObjectId(poll_id), "voters.user": ObjectId(current_user["_id"])}},
        # Group back the original document and add the choice as a new field
        {
            "$group": {
                "_id": "$_id",
                "original_doc": {"$first": "$$ROOT"},
                "user_choice": {"$first": "$voters.choice"}
            }
        },
        # Add the user's choice as a new field in the original document
        {
            "$addFields": {
                "original_doc.user_choice": "$user_choice"
            }
        },
        # Replace the root to get the original document with the new field
        {"$replaceRoot": {"newRoot": "$original_doc"}}
    ]
    search = await db.polls.aggregate(pipeline).to_list()
    poll = search[0]
    choices = [choice["body"] for choice in poll["choices"]]
    if choice.body not in choices:
        raise Exception
    if poll["closes"] < datetime.now(timezone.utc):
        raise Exception
    if poll["can_change_vote"] is False and poll["user_choice"] is not None:
        raise Exception
    await db.polls.update_one({"_id": poll["_id"]}, {"$set": {"voters.$[elem].choice": choice.body}},
                              array_filters=[{"elem.user": ObjectId(current_user["_id"])}])
    background_tasks.add_task(after_vote, poll_id)


@router.post("/", response_model=models.PollReferenceModel, dependencies=[Depends(discord.requires_authorization)])
async def post_poll(poll: models.PostPollModel, current_user: Annotated[dict, Depends(get_current_user)]):
    if current_user["dc_uuid"] != "928058365286973452":
        raise Exception
    current_datetime = datetime.now(timezone.utc)
    voters_query = {"inactive": False}
    if poll.party is not None:
        voters_query["party"] = ObjectId(poll.party)
    voters = [{"user": user["_id"], "choice": None} for user in await db.query_users(voters_query)]
    insert = await db.polls.insert_one({
        "title": poll.title,
        "proposal": poll.proposal,
        "secret": poll.secret,
        "choices": [choice.model_dump() for choice in poll.choices],
        "voters": voters,
        "timestamp": current_datetime,
        "closes": current_datetime + timedelta(days=3),
        "can_change_vote": True,
        "thresholds": thresholds(len(voters)),
    })
    return await db.get_poll({"_id": insert.inserted_id})
