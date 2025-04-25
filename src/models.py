from datetime import datetime
from typing import List, Union, Literal, Optional, Any

from bson import ObjectId
from fastapi_discord import User
from pydantic import BaseModel, Field, model_validator
from pydantic.functional_validators import BeforeValidator
from pydantic_core import core_schema
from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]


class ObjectIdType(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
            cls, _source_type: Any, _handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x),
                when_used='json'
            ),
        )

    @classmethod
    def validate(cls, value) -> ObjectId:
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")

        return ObjectId(value)


Pronoun = Literal['they', 'she', 'he', 'it', 'was']

Candidate = Literal[
    "Lemon / Xboy",
    "Pentagonal / v1scosity",
    "Gem / PetBat",
    "CiCi / General D"
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
    party: Optional[ObjectIdType] = None
    name: str


class ElectionCandidateModel(BaseModel):
    user: Optional[ObjectIdType] = None
    name: str


class ElectionTicketModel(BaseModel):
    id: ObjectIdType = Field(validation_alias="_id")
    candidate: ElectionCandidateModel
    running_mate: Optional[ElectionCandidateModel] = None
    campaign: Optional[ElectionCampaignModel] = None


class ElectionVoterModel(BaseModel):
    user: ObjectIdType
    voted: bool


class ElectionBallot(BaseModel):
    rankings: List[ObjectIdType]


# LIVE RESULTS ENDPOINT NOT NECESSARY
# IGNORE FOR NOW!!!
#
# how to write this aggregation
# match election
# map - remove eliminated candidates from ballots
# count all array elements at index 0
# REMEMBER: write new doc to temporary field;replace root with new field

class VoterStatusModel(BaseModel):
    id: str = Field(validation_alias="_id")
    open: bool
    user_is_voter: bool
    user_has_voted: bool
    user_can_vote: bool


class GetElectionModel(BaseModel):
    id: str = Field(validation_alias="_id")
    title: str
    choices: List[ElectionTicketModel]
    voters: List[ElectionVoterModel]
    total_voters: int
    total_voted: int


class ScheduleModel(BaseModel):
    opens: datetime
    closes: datetime


class InsertElectionModel(BaseModel):
    slug: str = Field(serialization_alias="_id")
    title: str
    visible: bool = False
    open: bool = False
    schedule: Optional[ScheduleModel] = Field(default=None)
    choices: List = []
    voters: List = []
    ballots: List = []


class InsertDocumentBaseModel(BaseModel):
    id: ObjectIdType = Field(default_factory=ObjectId, alias="_id")

    @model_validator(mode='before')
    def enforce_constant(cls, values):
        # Ensure the field is either not provided or matches the default value
        if "id" in values or "_id" in values:
            raise ValueError("id cannot be set.")
        return values


class InsertElectionCandidateModel(InsertDocumentBaseModel):
    candidate: ElectionCandidateModel
    running_mate: Optional[ElectionCandidateModel] = None
    campaign: Optional[ElectionCampaignModel] = None
