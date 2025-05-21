from typing import List
import asyncio
from unittest import case

from bson import CodecOptions, ObjectId
from pydantic import TypeAdapter

from database.db_connection import get_connection
from models.polls import PollModel, PollVoter, Ballot
from .pipelines import fixed_poll_voters_pipeline

options = CodecOptions(tz_aware=True)

client = get_connection()
db = client.get_database("strudel")

polls = db.get_collection("polls_v2", options)
voters = db.get_collection("polls_voters")
ballots = db.get_collection("polls_ballots")
users = db.get_collection("users")

def validate_ballot(poll: PollModel, ballot: Ballot):
    if ballot.ballot_type != poll.ballot_type:
        raise Exception("Mismatched ballot type")
    choices = [choice.id for choice in poll.choices]
    match ballot.ballot_type:
        case "irv":
            pass
        case "star":
            ballot_choices = [score.choice for score in ballot.scores]
            if not set(choices) == set(ballot_choices):
                raise Exception("Scored choices do not match poll choices")
        case "approval":
            pass
        case "choose-one":
            if not ballot.choice in choices:
                raise Exception("Invalid choice")

async def get_poll(poll_id: ObjectId) -> PollModel:
    search = await polls.find_one({"_id": poll_id})
    return PollModel(**search)

async def get_voter(poll_id: ObjectId, voter_id: ObjectId, dynamic=False) -> PollVoter:
    if dynamic is True:
        search = await voters.find_one({"poll": poll_id, "user": voter_id})
        if search is None:
            poll = await get_poll(poll_id)
            voter = await users.aggregate(fixed_poll_voters_pipeline({"_id": voter_id} | poll.voter_filter, poll.id)).to_list()
            if voter is None:
                raise Exception("Voter does not meet requirements")
            TypeAdapter(PollVoter).validate_python(voter[0])
            await voters.insert_one(voter[0])
    search = await voters.find_one({"poll": poll_id, "user": voter_id})
    return PollVoter(**search)

async def create_poll(poll: PollModel):
    inserted = await polls.insert_one(poll.model_dump(by_alias=True))
    if poll.dynamic_voters is False:
        poll_voters = await users.aggregate(fixed_poll_voters_pipeline(poll.voter_filter, inserted.inserted_id)).to_list()
        TypeAdapter(List[PollVoter]).validate_python(poll_voters)

        await voters.insert_many(poll_voters)

    return await get_poll(inserted.inserted_id)

# if all polls use the same lock, voting will absolutely be a bit slow
# ballot lock per user is the most straightforward way to do multiple locks
ballot_lock = asyncio.Lock()

async def cast_vote(poll_id: ObjectId, voter_id: ObjectId, ballot: Ballot):
    poll = await get_poll(poll_id)
    if poll.open is False:
        raise Exception("Poll is closed")
    validate_ballot(poll, ballot)
    async with ballot_lock:
        voter = await get_voter(poll_id, voter_id, dynamic=poll.dynamic_voters)
        if voter.voted is True:
            # support changing vote eventually
            raise Exception("User already voted")
        inserted_ballot = await ballots.insert_one({"poll": poll.id} | ballot.model_dump(by_alias=True))
        update = {"voted": True}
        if poll.secret is False:
            update["ballot"] = inserted_ballot.inserted_id
        await voters.update_one({"_id": voter.id}, {"$set": update})
        return





