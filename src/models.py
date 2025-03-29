from datetime import datetime
from typing import List, Union, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from pydantic.functional_validators import BeforeValidator
from fastapi_discord import User

from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

Pronoun = Literal['they', 'she', 'he', 'it', 'was']

Candidate = Literal[
    "Atlas / Azocir",
    "Pentagonal / Releporp",
]


class Ballot(BaseModel):
    first: Candidate

    @model_validator(mode='before')
    def alias_values(cls, values):
        seen = set()
        for vote in ["first"]:
            if values[vote] in seen:
                raise ValueError(f"Duplicate vote in ballot")
            seen.add(values[vote])
        return values


class ErrorModel(BaseModel):
    error: str
    message: str


class DocumentModel(BaseModel):
    id: PyObjectId

    @model_validator(mode='before')
    def alias_values(cls, values):
        values['id'] = values.pop("_id")
        return values


class UserPartyModel(DocumentModel):
    name: str
    shorthand: str
    color: str


class UserModel(DocumentModel):
    name: str
    dc_uuid: str
    mc_uuid: str
    party: Union[UserPartyModel, None]


class PartyMemberModel(DocumentModel):
    name: str


class PartyLeaderModel(DocumentModel):
    name: str


class PartyModel(DocumentModel):
    name: str
    shorthand: str
    color: str
    leader: Union[PartyLeaderModel, None]


class UserCollection(BaseModel):
    users: List[UserModel]


class PartyCollection(BaseModel):
    parties: List[PartyModel]


class UserAccountModel(DocumentModel):
    name: str
    dc_uuid: str
    mc_uuid: str


class SessionInfoModel(DocumentModel):
    discord: User
    user: UserAccountModel


class RegistrationModel(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    pronouns: Pronoun


class ServerInfoModel(BaseModel):
    login_url: str


class AuthCallbackModel(BaseModel):
    access_token: str
    refresh_token: str

class VoterStatusModel(BaseModel):
    allowed: bool
    reason: str


class PostProposalModel(BaseModel):
    title: str = Field(max_length=70)
    body: str = Field(max_length=10000)


class ReviseProposalModel(BaseModel):
    body: str = Field(max_length=10000)


class ProposalRevisionModel(BaseModel):
    body: str = Field(max_length=10000)
    timestamp: datetime


class ProposalModel(DocumentModel):
    title: str
    author: UserModel
    invalid: bool
    rejection_reason: str
    revisions: List[ProposalRevisionModel]
    revisions_allowed: bool


class ProposalReferenceModel(DocumentModel):
    title: str
    author: UserModel
    invalid: bool


class ProposalCollection(BaseModel):
    proposals: List[ProposalReferenceModel]


class PollChoice(BaseModel):
    body: str


class PollChoiceResultsModel(PollChoice):
    votes: int


class PostPollModel(BaseModel):
    title: str
    choices: List[PollChoice] = Field(default=[PollChoice(body="Yes"), PollChoice(body="No")])
    proposal: int
    secret: bool = Field(default=False)
    party: Optional[str] = Field(default=None)


class PollReferenceModel(DocumentModel):
    title: str
    choices: List[PollChoiceResultsModel]
    proposal: int
    total_voters: int


class PollCollection(BaseModel):
    polls: List[PollReferenceModel]


class PollVoterModel(BaseModel):
    user: UserModel
    choice: Union[str, None]


class PollModel(PollReferenceModel):
    voters: List[PollVoterModel]


class PostPollVoteModel(BaseModel):
    body: str

# elections models start

class ElectionCampaignModel(BaseModel):
    party: Optional[PyObjectId]
    name: str

class ElectionCandidateModel(BaseModel):
    user: PyObjectId
    name: str

class ElectionTicketModel(DocumentModel):
    candidate: ElectionCandidateModel
    running_mate: Optional[ElectionCandidateModel]
    name: str
    campaign: Optional[ElectionCampaignModel]

class ElectionVoterModel(BaseModel):
    user: UserModel
    voted: bool

class ElectionBallot(BaseModel):
    rankings: list
# LIVE RESULTS ENDPOINT NOT NECESSARY
# IGNORE FOR NOW!!!
#
# how to write this aggregation
# match election
# map - remove eliminated candidates from ballots
# count all array elements at index 0
# REMEMBER: write new doc to temporary field;replace root with new field
class ElectionModel(DocumentModel):
    title: str
    choices: List[ElectionTicketModel]
    voters: List[ElectionVoterModel]
    ballots: List[ElectionBallot]
