import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from database import InvalidBallotException
from models import InsertElectionModel, InsertElectionCandidateModel, ElectionBallot, GetElectionModel, VoterStatusModel
from shared import db, get_current_user, discord

router = APIRouter(prefix="/elections", tags=["Elections"])


async def elections_permission(current_user: Annotated[dict, Depends(get_current_user)]):
    if not await db.user_has_permission(current_user["_id"], "manage_elections"):
        raise HTTPException(status_code=403)


manage_election_deps = dependencies = [Depends(discord.requires_authorization), Depends(elections_permission)]


async def ballot_valid(election: str, ballot: ElectionBallot):
    try:
        check = await db.is_ballot_valid(election, ballot)
        if check:
            return True
        else:
            raise HTTPException(status_code=500,
                                detail="Ballot validation failed for unknown reason, you should not see this error ever.")
    except InvalidBallotException as e:
        raise HTTPException(status_code=422, detail=e.args[0])


async def election_exists(election: str):
    search = await db.elections.find_one({"_id": election})
    if search is None:
        raise HTTPException(status_code=404)


async def user_can_vote(current_user: Annotated[dict, Depends(get_current_user)], election: str,
                        _election_exists=Depends(election_exists)):
    status = await db.get_voter_status(current_user["_id"], election)
    print(status)
    if not status.user_can_vote:
        raise HTTPException(status_code=403)


@router.get("/{election}", response_model=GetElectionModel, dependencies=[Depends(election_exists)])
async def get_election(election: str):
    pipeline = [
        {
            '$match': {"_id": election}
        }, {
            '$addFields': {
                'total_voters': {
                    '$size': '$voters'
                },
                'total_voted': {
                    '$size': {
                        '$filter': {
                            'input': '$voters',
                            'as': 'voter',
                            'cond': {
                                '$eq': [
                                    '$$voter.voted', True
                                ]
                            }
                        }
                    }
                }
            }
        }, {
            '$project': {
                'ballots': 0
            }
        }
    ]
    search = await db.elections.aggregate(pipeline).to_list()
    return search[0]


@router.get("/{election}/voter_status", response_model=VoterStatusModel,
            dependencies=[Depends(discord.requires_authorization), Depends(election_exists)])
async def get_voter_status(election: str, current_user: Annotated[dict, Depends(get_current_user)]):
    status = await db.get_voter_status(current_user["_id"], election)
    return status


@router.post("/", dependencies=manage_election_deps)
async def post_election(election: InsertElectionModel):
    result = await db.elections.insert_one(election.model_dump(by_alias=True))


@router.post("/{election}/candidate", dependencies=manage_election_deps)
async def post_election_candidate(election: str, candidate: InsertElectionCandidateModel):
    await db.elections.update_one({"_id": election}, {"$push": {"choices": candidate.model_dump(by_alias=True)}})


@router.post("/{election}/add_voters", dependencies=manage_election_deps + [Depends(election_exists)])
async def add_voters(election: str):
    search = await db.elections.find_one({"_id": election})
    if search["open"] is True:
        raise HTTPException(status_code=403, detail="This election is already open.")
    if search.get("voter_filter") is None:
        raise HTTPException(status_code=500, detail="No voter filter specified.")
    pipeline = [
        {
            '$match': search["voter_filter"]
        }, {
            '$set': {
                'voted': False
            }
        }, {
            '$project': {
                'user': '$_id',
                'voted': 1,
                'party': 1,
                '_id': 0
            }
        }
    ]
    voters = await db.users.aggregate(pipeline).to_list()
    update = {
        "$set": {"voters": voters}
    }
    await db.elections.update_one({"_id": election}, update)


# could probably do a dictionary system to have each election use its own lock
# but like. we won't have that many people casting votes at the same time
ballot_lock = asyncio.Lock()


@router.post("/{election}/vote",
             dependencies=[Depends(discord.requires_authorization), Depends(election_exists), Depends(ballot_valid)])
async def post_election_vote(current_user: Annotated[dict, Depends(get_current_user)], election: str,
                             ballot: ElectionBallot):
    update = {
        "$set": {
            "voters.$.voted": True
        },
        "$push": {
            "ballots": ballot.rankings
        }
    }

    async with ballot_lock:
        status = await db.get_voter_status(current_user["_id"], election)
        print(status)
        if not status.user_can_vote:
            raise HTTPException(status_code=403)
        elif status.user_can_vote:
            await db.elections.update_one({"_id": election, "voters.user": current_user["_id"]}, update)
            return "voted!"
