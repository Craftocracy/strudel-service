from bson import ObjectId


def fixed_poll_voters_pipeline(voter_filter: dict, poll: ObjectId):
    return [
        {
            '$match': voter_filter,
        }, {
            '$project': {
                'poll': poll,
                'user': '$_id',
                '_id': 0
            }
        }, {
            '$set': {
                'ballot': None,
                'voted': False
            }
        }
    ]