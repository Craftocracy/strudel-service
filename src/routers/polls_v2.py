from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from database import polls
from database.polls import create_poll, cast_vote, get_poll, users, voters, process_results
from models import ObjectIdType
from models.polls import PollModel, PostBallot, TempVoterStatus, PollWithResultsModel
from shared import discord, db, get_current_user, maybe_get_current_user


async def manage_polls_permission(current_user: Annotated[dict, Depends(get_current_user)]):
    if not await db.user_has_permission(current_user["_id"], "manage_polls"):
        raise HTTPException(status_code=403)


manage_election_deps = [Depends(discord.requires_authorization), Depends(manage_polls_permission)]

router = APIRouter(prefix="/polls", tags=["Polls"])

@router.get("/{poll_id}", response_model=PollModel)
async def get__poll(poll_id: ObjectIdType):
    poll = await get_poll(poll_id)
    return poll

@router.post("/", dependencies=manage_election_deps, response_model=PollModel)
async def post_poll(poll: PollModel):
    inserted_poll = await create_poll(poll)
    return inserted_poll

@router.post("/{poll_id}/vote", dependencies=[Depends(discord.requires_authorization)])
async def post_poll_vote(poll_id: ObjectIdType, ballot: PostBallot, current_user: Annotated[dict, Depends(get_current_user)]):
    print(ballot.model_dump())
    await cast_vote(poll_id, current_user["_id"], ballot.ballot)
    return

@router.get("/{poll_id}/process_results", dependencies=manage_election_deps)
async def process_poll_results(poll_id: ObjectIdType):
    return await process_results(poll_id)

@router.get("/{poll_id}/results", response_model=PollWithResultsModel)
async def get_poll_results(poll_id: ObjectIdType, current_user: Annotated[dict, Depends(maybe_get_current_user)]):
    search = await polls.polls.find_one({"_id": poll_id})
    poll = PollWithResultsModel(**search)
    if not poll.results.public:
        if current_user is None:
            raise Exception
        if not await db.user_has_permission(current_user["_id"], "manage_polls"):
            raise HTTPException(status_code=403)
    return poll


@router.get("/{poll_id}/voter_status", dependencies=[Depends(discord.requires_authorization)], response_model=TempVoterStatus)
async def temp_voter_status(poll_id: ObjectIdType, current_user: Annotated[dict, Depends(get_current_user)]):
    poll = await get_poll(poll_id)
    if poll.open is False:
        return {"can_vote": False, "reason": "Poll is closed"}
    voter = await voters.find_one({"poll": poll_id, "user": current_user["_id"]})
    if voter is None:
        if poll.dynamic_voters is True:
            user_search = await users.find_one({"_id": current_user["_id"]} | poll.voter_filter.model_dump(exclude_none=True))
            if user_search is None:
                return {"can_vote": False, "reason": "User is not eligible to vote in poll"}
            else:
                return {"can_vote": True, "reason": ""}
        else:
            return {"can_vote": False, "reason": "User is not eligible to vote in poll"}
    if voter["voted"] is True:
        return {"can_vote": False, "reason": "User has already voted"}
    else:
        return {"can_vote": True, "reason": ""}