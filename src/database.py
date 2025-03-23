from bson.codec_options import CodecOptions
import motor.motor_asyncio
from pymongo import ReturnDocument

options = CodecOptions(tz_aware=True)


class Database:
    def __init__(self, uri: str):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self._db = self._client.get_database("strudel")
        self.users = self._db.get_collection("users")
        self.parties = self._db.get_collection("parties")
        self.elections = self._db.get_collection("elections")
        self.proposals = self._db.get_collection("proposals")
        self.polls = self._db.get_collection("polls", options)
        self.counters = self._db.get_collection("counters")

    async def get_next_sequence_value(self, sequence_name):
        """Get the next sequence value for a given sequence name."""
        result = await self.counters.find_one_and_update(
            {'_id': sequence_name},
            {'$inc': {'sequence_value': 1}},
            return_document=ReturnDocument.AFTER,
            upsert=True
        )
        return result['sequence_value']

    async def query_parties(self, query: dict) -> list:
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

    async def query_users(self, query: dict) -> list:
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

    async def query_proposals(self, query: dict) -> list:
        pipeline = [
            {"$match": query},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "author",
                    "foreignField": "_id",
                    "as": "author"
                }
            },
            {"$unwind": {"path": "$author", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "parties",
                    "localField": "author.party",
                    "foreignField": "_id",
                    "as": "author.party"
                }
            },
            {"$unwind": {"path": "$author.party", "preserveNullAndEmptyArrays": True}},
            {
                "$addFields": {
                    "author.party": {"$ifNull": ["$author.party", None]}
                }
            }
        ]
        result = await self.proposals.aggregate(pipeline).to_list()
        return result

    async def query_polls(self, query: dict, respect_secrets: bool = True) -> list:
        pipeline = [
            {"$match": query},
            {
                '$unwind': '$voters'
            }, {
                '$lookup': {
                    'from': 'users',
                    'localField': 'voters.user',
                    'foreignField': '_id',
                    'as': 'voter_user'
                }
            }, {
                '$unwind': '$voter_user'
            }, {
                '$lookup': {
                    'from': 'parties',
                    'localField': 'voter_user.party',
                    'foreignField': '_id',
                    'as': 'voter_user_party'
                }
            }, {
                '$unwind': {
                    'path': '$voter_user_party',
                    'preserveNullAndEmptyArrays': True
                }
            }, {
                '$addFields': {
                    'voter_user.party': {
                        '$cond': {
                            'if': {
                                '$eq': [
                                    '$voter_user.party', None
                                ]
                            },
                            'then': None,
                            'else': '$voter_user_party'
                        }
                    }
                }
            }, {
                '$group': {
                    '_id': '$_id',
                    'originalFields': {
                        '$first': '$$ROOT'
                    },
                    'voters': {
                        '$push': {
                            'user': '$voter_user',
                            'choice': '$voters.choice'
                        }
                    }
                }
            }, {
                '$replaceRoot': {
                    'newRoot': {
                        '$mergeObjects': [
                            '$originalFields', {
                                'voters': '$voters'
                            }
                        ]
                    }
                }
            }, {
                '$unwind': '$choices'
            }, {
                '$lookup': {
                    'from': 'polls',
                    'localField': 'choices.body',
                    'foreignField': 'voters.choice',
                    'as': 'votes'
                }
            }, {
                '$addFields': {
                    'choices.votes': {
                        '$size': {
                            '$filter': {
                                'input': '$voters',
                                'as': 'voter',
                                'cond': {
                                    '$eq': [
                                        '$$voter.choice', '$choices.body'
                                    ]
                                }
                            }
                        }
                    }
                }
            }, {
                '$group': {
                    '_id': '$_id',
                    'originalFields': {
                        '$first': '$$ROOT'
                    },
                    'choices': {
                        '$push': '$choices'
                    }
                }
            }, {
                '$replaceRoot': {
                    'newRoot': {
                        '$mergeObjects': [
                            '$originalFields', {
                                'choices': '$choices'
                            }
                        ]
                    }
                }
            }, {
                '$addFields': {
                    'total_voters': {
                        '$size': '$voters'
                    }
                }
            },
            {"$sort": {"_id": 1}}
        ]
        result = await self.polls.aggregate(pipeline).to_list()
        if respect_secrets is True:
            for poll in result:
                if poll["secret"] is True:
                    poll["voters"] = []
                    if poll["can_change_vote"] is True:
                        for choice in poll["choices"]:
                            choice["votes"] = 0
        return result

    async def get_poll(self, query: dict, respect_secrets: bool = True) -> dict:
        search = await self.query_polls(query, respect_secrets=respect_secrets)
        if len(search) == 0:
            raise KeyError
        return search[0]

    async def get_proposal(self, query: dict) -> dict:
        search = await self.query_proposals(query)
        if len(search) == 0:
            raise KeyError
        return search[0]

    async def get_party(self, query: dict) -> dict:
        search = await self.query_parties(query)
        if len(search) == 0:
            raise KeyError
        return search[0]

    async def get_user(self, query: dict) -> dict:
        search = await self.query_users(query)
        if len(search) == 0:
            raise KeyError
        return search[0]
