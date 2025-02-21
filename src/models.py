from datetime import datetime
from typing import List, Union, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from pydantic.functional_validators import BeforeValidator
from fastapi_discord import User

from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

Pronoun = Literal['they', 'she', 'he', 'it', 'was']

Candidate = Literal[
    "CiCi / Sol",
    "dominoexists / PetBat",
    "Pentagonal / poop barrel",
    "milowyorhi / Alibaba"
]

class Ballot(BaseModel):
    first: Candidate
    second: Candidate
    third: Candidate
    fourth: Candidate
    @model_validator(mode='before')
    def alias_values(cls, values):
        seen = set()
        for vote in ["first", "second", "third", "fourth"]:
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
    members: List[PartyMemberModel]
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

class ElectionModel(BaseModel):
    voters: List[PartyMemberModel]
    votes_cast: int

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