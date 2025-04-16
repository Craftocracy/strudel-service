import discord
from shared import config, db

intents = discord.Intents.default()
intents.message_content = True

client = discord.Bot(intents=intents)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.command(description="Sends the current party active membership breakdown") # this decorator makes a slash command
async def leaderboard(ctx): # a slash command will be created with the name "ping"
    pipeline = [
        {
            '$match': {
                'inactive': False
            }
        }, {
            '$group': {
                '_id': '$party',
                'count': {
                    '$sum': 1
                }
            }
        }, {
            '$lookup': {
                'from': 'parties',
                'localField': '_id',
                'foreignField': '_id',
                'as': 'partyDetails'
            }
        }, {
            '$unwind': {
                'path': '$partyDetails',
                'preserveNullAndEmptyArrays': True
            }
        }, {
            '$project': {
                '_id': 0,
                'party': {
                    '$cond': {
                        'if': {
                            '$eq': [
                                '$_id', None
                            ]
                        },
                        'then': 'Independent/Unaffiliated',
                        'else': '$partyDetails.name'
                    }
                },
                'count': 1
            }
        }, {
            '$group': {
                '_id': None,
                'total': {
                    '$sum': '$count'
                },
                'parties': {
                    '$push': {
                        'party': '$party',
                        'count': '$count'
                    }
                }
            }
        }, {
            '$unwind': '$parties'
        }, {
            '$project': {
                '_id': 0,
                'party': '$parties.party',
                'count': '$parties.count',
                'percentage': {
                    '$round': [
                        {
                            '$multiply': [
                                {
                                    '$divide': [
                                        '$parties.count', '$total'
                                    ]
                                }, 100
                            ]
                        }, 2
                    ]
                }
            }
        }, {
            '$sort': {
                'count': -1
            }
        }
    ]
    db_leaderboard = await db.users.aggregate(pipeline).to_list()
    msg = ""
    for party in db_leaderboard:
        msg += f"{party["party"]} - {party["percentage"]}% ({str(party["count"])})\n"

    await ctx.respond(msg)

async def notify(message: str):
    channel = await client.fetch_channel(config["discord"]["notifications_channel"])
    await channel.send(message)

