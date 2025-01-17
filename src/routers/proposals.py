from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends
from shared import db, get_current_user, requires_registration, discord
import models
import datetime
router = APIRouter(prefix="/proposals", tags=["Legislature", "Proposals"])

## OK SWEETIE
# in original struedl service you made class for users, it accessed the document wit stored id, stored a reference to the database in it. DO IT AGAIN!!

# author objectid conversion could probably be a dependency
@router.get("/", response_model=models.ProposalCollection)
async def query_proposals(author: str | None = None):
    query = {}
    if author:
        query["author"] = ObjectId(author)
    search = await db.proposals.find(query).to_list()
    print(search)
    return {"proposals": search}



@router.post("/", response_model=models.PostProposalResponse, dependencies=[Depends(requires_registration), Depends(discord.requires_authorization)])
async def post_proposal(proposal: models.PostProposal, current_user: Annotated[dict, Depends(get_current_user)]):
   result = await db.proposals.insert_one({
       "title": proposal.title,
       "comment": proposal.comment,
       "effect": proposal.effect,
       "author": current_user["_id"],
   })
   return {"id": result.inserted_id}