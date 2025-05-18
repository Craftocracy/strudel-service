import os
import yaml
from motor.motor_asyncio import AsyncIOMotorClient

with open(os.path.join(os.environ["DATADIR"], "config.yml"), 'r') as file:
    config: dict = yaml.safe_load(file)

def get_connection() -> AsyncIOMotorClient:
    if not hasattr(get_connection, "conn"):
        print("connecting to database")
        get_connection.conn = AsyncIOMotorClient(config["database"]["strudel"]["mongo_uri"])
    return get_connection.conn

