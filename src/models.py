from typing import Optional, List, Union, Literal
from pydantic import BaseModel, Field, model_validator
from pydantic.functional_validators import BeforeValidator
from fastapi_discord import User
from shared import db

from typing_extensions import Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

Pronoun = Literal['they', 'she', 'he', 'it']

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
    name: str = Field(min_length=1, max_length=32)
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
    name: str
    pronouns: Pronoun

class ServerInfoModel(BaseModel):
    login_url: str

class AuthCallbackModel(BaseModel):
    access_token: str
    refresh_token: str
