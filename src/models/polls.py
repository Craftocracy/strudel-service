from datetime import datetime
from typing import List, Union, Literal, Dict, Annotated, Optional, Tuple
from pydantic import BaseModel, Field, conint

from models import ObjectIdType, InsertDocumentBaseModel, ElectionCandidateModel, ElectionCampaignModel, \
    current_time_factory


# ballots
class LegacyInstantRunoffBallot(InsertDocumentBaseModel):
    ballot_type: Literal["irv-legacy"]
    ## LEGACY IRV VOTING WONT BE SUPPORTED  DONT BOTHER VALIDATING
    rankings: Dict[str, str]

class InstantRunoffBallot(InsertDocumentBaseModel):
    ballot_type: Literal["irv"]
    rankings: List[ObjectIdType]

class ChoiceScore(BaseModel):
    choice: ObjectIdType
    score: int = Field(ge=0, le=5)

class StarBallot(InsertDocumentBaseModel):
    ballot_type: Literal["star"]
    scores: List[ChoiceScore]

class ApprovalBallot(InsertDocumentBaseModel):
    ballot_type: Literal["approval"]
    approve: bool | None

class ChooseOneBallot(InsertDocumentBaseModel):
    ballot_type: Literal["choose-one"]
    choice: ObjectIdType

ballot_type = Literal["irv", "star", "approval", "choose-one"]
Ballot = Union[InstantRunoffBallot, StarBallot, ApprovalBallot, ChooseOneBallot]

class PostBallot(BaseModel):
    ballot: Ballot = Field(discriminator="ballot_type")

# choices
class ElectionChoice(InsertDocumentBaseModel):
    candidate: ElectionCandidateModel
    running_mate: Optional[ElectionCandidateModel] = None
    campaign: Optional[ElectionCampaignModel] = None

class TextChoice(InsertDocumentBaseModel):
    text: str


PollChoice = Union[TextChoice, ElectionChoice]
# voters
class PollVoter(InsertDocumentBaseModel):
    poll: ObjectIdType
    user: ObjectIdType
    ballot: ObjectIdType | None
    voted: bool


class TempVoterStatus(BaseModel):
    can_vote: bool
    reason: str

# star results model

class StarMatchupResults(BaseModel):
    win: int
    lose: int
    tie: int

class StarResults(BaseModel):
    results_type: Literal["star"]
    total_scores: Dict[str, int]
    highlighted_races: List[Tuple[str, str]] = []
    preference_matrix: Dict[str, Dict[str, StarMatchupResults ]]

# polls
PollResults = Union[StarResults]

class PollResultsModel(BaseModel):
    public: bool = False
    data: Optional[PollResults] = Field(discriminator="results_type", default=None)

class PollModel(InsertDocumentBaseModel):
    title: str
    choices: List[PollChoice]
    timestamp: datetime = Field(default_factory=current_time_factory)
    open: bool = True
    ballot_type: ballot_type
    voter_filter: dict = {"inactive": False}
    dynamic_voters: bool = False
    secret: bool = False

class PollWithResultsModel(PollModel):
    results: PollResultsModel

