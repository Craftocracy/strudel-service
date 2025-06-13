import itertools
import pprint
from collections import OrderedDict
from typing import List, Dict
import asyncio
from unittest import case

from bson import CodecOptions, ObjectId
from pydantic import TypeAdapter

from database.db_connection import get_connection
from models import ObjectIdType
from models.polls import PollModel, PollVoter, Ballot, StarBallot, ElectionChoice
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
            voter = await users.aggregate(fixed_poll_voters_pipeline({"_id": voter_id} | poll.voter_filter.model_dump(exclude_none=True), poll.id)).to_list()
            if voter is None:
                raise Exception("Voter does not meet requirements")
            TypeAdapter(PollVoter).validate_python(voter[0])
            await voters.insert_one(voter[0])
    search = await voters.find_one({"poll": poll_id, "user": voter_id})
    return PollVoter(**search)

async def create_poll(poll: PollModel):
    inserted = await polls.insert_one(poll.model_dump(by_alias=True))
    if poll.dynamic_voters is False:
        poll_voters = await users.aggregate(fixed_poll_voters_pipeline(poll.voter_filter.model_dump(exclude_none=True), inserted.inserted_id)).to_list()
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



async def process_results(poll_id: ObjectId):
    poll = await get_poll(poll_id)
    candidates = {choice.id: choice for choice in poll.choices}
    if poll.ballot_type == "star":
        poll_ballots: list[StarBallot] = [StarBallot(**b) for b in await ballots.find({"poll": poll.id}).to_list()]
        # TOTAL SCORES
        total_scores: Dict[str, int] = {}
        for score in [score for ballot in poll_ballots for score in ballot.scores]:
            total_scores.setdefault(str(score.choice), 0)
            total_scores[str(score.choice)] += score.score
        ordered_total_scores = OrderedDict(
            sorted(total_scores.items(), key=lambda item: item[1], reverse=True)
        )
        # PREFERENCE MATRIX
        indexed_ballots = [{score.choice: score.score for score in ballot.scores} for ballot in poll_ballots]
        matrix = {}
        for candidate_a, candidate_b in itertools.permutations(poll.choices, 2):
            matrix.setdefault(str(candidate_a.id), {})
            win = 0
            lose = 0
            tie = 0
            for ballot in indexed_ballots:
                if ballot[candidate_a.id] > ballot[candidate_b.id]:
                    win += 1
                elif ballot[candidate_a.id] < ballot[candidate_b.id]:
                    lose += 1
                else:
                    tie += 1
            matrix[str(candidate_a.id)][str(candidate_b.id)] = {"win": win, "lose": lose, "tie": tie}
        await polls.update_one({"_id": poll.id}, {"$set": {"results.data.results_type": "star", "results.data.total_scores": ordered_total_scores,"results.data.preference_matrix": matrix}})








