import motor.motor_asyncio

class Database:
    def __init__(self, uri: str):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self._db = self._client.strudel
        self.users = self._db.get_collection("users")
        self.parties = self._db.get_collection("parties")

    async def resolve_user_references(self, user: dict):
        if user["party"] is not None:
            user["party"] = await self.parties.find_one({"_id": user["party"]})
        return user

    async def resolve_party_references(self, party: dict):
        if party["leader"] is not None:
            party["leader"] = await self.users.find_one({"_id": party["leader"]})
        party["members"] = await self.users.find({"party": party["_id"]}).to_list()
        return party

    async def query_parties(self):
        result = []
        async for party in self.parties.find():
            result.append(await self.resolve_party_references(party))
        return result

    async def query_users(self):
        result = []
        async for user in self.users.find():
            result.append(await self.resolve_user_references(user))
        return result

    async def get_party(self, party_id):
        try:
            return await self.parties.find_one({"_id": party_id})
        except KeyError:
            raise KeyError
    async def get_user(self, query):
        if type(query) == str:
            query = {"_id": query}
        try:
            search = await self.users.find_one(query)
            if search is None:
                return None
            return await self.resolve_user_references(search)
        except KeyError:
            raise KeyError

