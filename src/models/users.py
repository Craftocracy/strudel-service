import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

from models import ObjectIdType

FractionType = List[int, int]
Pronoun = Literal['they', 'she', 'he', 'it']


class UserAffiliation(BaseModel):
    party: ObjectIdType
    seat: FractionType
    joined: datetime
    leader: bool
    founding_member: bool


class DiscordLink(BaseModel):
    id: int


class MinecraftLink(BaseModel):
    uuid: str


class PlanLink(BaseModel):
    username: str
    last_seen: datetime


class UserLinks(BaseModel):
    discord: DiscordLink
    minecraft: MinecraftLink
    # plan: PlanLink


class UserProfile(BaseModel):
    bio: str = Field(max_length=1000)
    pronouns: str = Field(max_length=16)


class UserFlags(BaseModel):
    inactive: bool


class User(BaseModel):
    id: ObjectIdType = Field(validation_alias="_id")
    name: str
    pronouns: Pronoun
    links: UserLinks
    roles: List[str]
    flags: UserFlags
    party: ObjectIdType