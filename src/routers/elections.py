from fastapi import APIRouter
from shared import db

router = APIRouter(prefix="/elections", tags=["Elections"])


