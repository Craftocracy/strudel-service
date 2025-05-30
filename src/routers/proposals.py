import datetime
from typing import Annotated, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import models
from bot import bot
from shared import db, get_current_user, discord, webapp_page

router = APIRouter(prefix="/proposals", tags=["Proposals"])


class FilterParams(BaseModel):
    author: Optional[str] = None
    invalid: Optional[bool] = None


@router.get("/", response_model=models.ProposalCollection)
async def get_proposals(filter_query: Annotated[FilterParams, Query()]):
    query = filter_query.model_dump(exclude_unset=True)
    if query.get("author"):
        query["author"] = ObjectId(query.pop("author"))
    return {"proposals": await db.query_proposals(query)}


@router.get("/{proposal}", response_model=models.ProposalModel)
async def get_proposal(proposal: int):
    return await db.get_proposal({"_id": proposal})


@router.post("/", dependencies=[Depends(discord.requires_authorization)], response_model=models.ProposalReferenceModel)
async def post_proposal(proposal: models.PostProposalModel, current_user: Annotated[dict, Depends(get_current_user)],
                        background_tasks: BackgroundTasks):
    s = await db.get_next_sequence_value("proposals")
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
    await db.proposals.insert_one({
        "_id": s,
        "author": current_user["_id"],
        "title": proposal.title,
        "invalid": False,
        "rejection_reason": "",
        "revisions_allowed": True,
        "revisions": [
            {"timestamp": timestamp, "body": proposal.body}
        ],
    })
    background_tasks.add_task(bot.notify,
                              message=f"New proposal added by <@{current_user['dc_uuid']}>: {proposal.title}\n"
                                      f"<{webapp_page(f"/proposals/{str(s)}")}>")
    return await db.get_proposal({"_id": s})


@router.post("/{proposal}/revise", dependencies=[Depends(discord.requires_authorization)],
             response_model=models.ProposalReferenceModel)
async def revise_proposal(proposal: int, revision: models.ReviseProposalModel,
                          current_user: Annotated[dict, Depends(get_current_user)]):
    proposal = await db.get_proposal({"_id": proposal})
    if proposal["author"]["_id"] != current_user["_id"]:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    if proposal["revisions_allowed"] is False:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    db.proposals.update_one(
        {"_id": proposal["_id"]},
        {"$push": {"revisions": {"timestamp": datetime.datetime.now(tz=datetime.timezone.utc), "body": revision.body}}}
    )
    return await db.get_proposal({"_id": proposal["_id"]})
