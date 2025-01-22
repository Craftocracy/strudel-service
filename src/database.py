import motor.motor_asyncio
from bson import ObjectId

class Database:
    def __init__(self, uri: str):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self._db = self._client.strudel
        self.users = self._db.get_collection("users")
        self.parties = self._db.get_collection("parties")
        self.elections = self._db.get_collection("elections")

    async def query_parties(self, query: dict = None):
        if query is None:
            query = {}
        pipeline = [
            {"$match": query},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "leader",
                    "foreignField": "_id",
                    "as": "leader"
                }
            },
            {"$unwind": {"path": "$leader", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "_id",
                    "foreignField": "party",
                    "as": "members"
                }
            },
            {
                "$addFields": {
                    "party": {"$ifNull": ["$leader", None]}
                }
            }
        ]
        result = await self.parties.aggregate(pipeline).to_list()
        return result

    async def query_users(self, query: dict = None) -> list:
        if query is None:
            query = {}
        pipeline = [
            {"$match": query},
            {
                "$lookup": {
                    "from": "parties",
                    "localField": "party",
                    "foreignField": "_id",
                    "as": "party"
                }
            },
            {"$unwind": {"path": "$party", "preserveNullAndEmptyArrays": True}},
            {
                "$addFields": {
                    "party": {"$ifNull": ["$party", None]}
                }
            }
        ]
        result = await self.users.aggregate(pipeline).to_list()
        return result
    async def get_party(self, party_id: ObjectId | str):
        search = await self.query_parties({"_id": ObjectId(party_id)})
        if len(search) == 0:
            raise KeyError
        return search[0]

    async def get_user(self, user_id: ObjectId | str):
        search = await self.query_users({"_id": ObjectId(user_id)})
        if len(search) == 0:
            raise KeyError
        return search[0]
