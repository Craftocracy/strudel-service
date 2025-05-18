from typing import List, Union, Literal
from pydantic import BaseModel, Field

from models import ObjectIdType

# ballots

class LegacyInstantRunoffBallot(BaseModel):
    ballot_type: Literal["irv-legacy"]

class InstantRunoffBallot(BaseModel):
    ballot_type: Literal["irv"]
    rankings: List[ObjectIdType]

class StarBallot(BaseModel):
    ballot_type: Literal["star"]

class LegislativeBallot(BaseModel):
    ballot_type: Literal["referendum"]

class PostBallot(BaseModel):
    ballot: InstantRunoffBallot | StarBallot = Field(discriminator="ballot_type")