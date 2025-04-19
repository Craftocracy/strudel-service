import discord
from bson import ObjectId
from discord.ext.commands import Context
from discord.types.interactions import InteractionContextType
from catppuccin import PALETTE

from shared import config, db, webapp_page

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

client = discord.Bot(intents=intents)

def global_command(**kwargs):
    # This function returns a pre-configured slash_command decorator
    def decorator(func):
        # Use the original @client.slash_command with pre-filled arguments
        return client.slash_command(
            contexts={
                discord.InteractionContextType.guild,
                discord.InteractionContextType.bot_dm,
                discord.InteractionContextType.private_channel,
            },
            integration_types={
                discord.IntegrationType.user_install,
                discord.IntegrationType.guild_install,
            },
            **kwargs
        )(func)  # Pass the function to the original decorator
    return decorator

def get_color(color: str):
    hexc = getattr(PALETTE.latte.colors, color).hex
    color_int = int(hexc.lstrip("#"), 16)
    return color_int

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
discord.Colour.blurple()
@global_command(description="Find a user's Strudel Service account")
async def whois(ctx: discord.ApplicationContext, user: discord.Option(discord.User)):
    try:
        strudel_user = await db.get_user({"dc_uuid": str(user.id)})
        registration_date = str(int(ObjectId(strudel_user["_id"]).generation_time.timestamp()))
        if strudel_user["party"] is None:
            strudel_user["party"] = {"name": "Independent/Unaffiliated", "shorthand": "I", "color": "text"}
        if strudel_user["inactive"] is True:
            status = "Inactive"
        else:
            status = "Active"
        embed = discord.Embed(
            title="User info",
            color=get_color(strudel_user["party"]["color"])
        )
        embed.add_field(name="User", value=f"[{strudel_user['name']}]({webapp_page(f"/users/{strudel_user['_id']}")})", inline=True)
        embed.add_field(name="Discord", value=f"<@{strudel_user['dc_uuid']}>", inline=True)
        embed.add_field(name="Party", value=f"[{strudel_user["party"]["shorthand"]}] {strudel_user["party"]["name"]}", inline=False)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Registration Date", value=f"<t:{registration_date}:F> (<t:{registration_date}:R>)", inline=False)
        await ctx.respond(embed=embed)
    except KeyError:
        await ctx.respond("No Strudel user found.")



@global_command(description="Sends the current party active membership breakdown") # this decorator makes a slash command
async def leaderboard(ctx: discord.ApplicationContext): # a slash command will be created with the name "ping"
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

