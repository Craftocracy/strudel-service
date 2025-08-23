import os
import yaml
from motor.motor_asyncio import AsyncIOMotorClient
from shared import config

def get_connection() -> AsyncIOMotorClient:
    if not hasattr(get_connection, "conn"):
        print("connecting to database")
        get_connection.conn = AsyncIOMotorClient(config.database.mongo)
    return get_connection.conn

