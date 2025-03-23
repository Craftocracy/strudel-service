import discord
from shared import config

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


async def notify(message: str):
    channel = await client.fetch_channel(config["discord"]["notifications_channel"])
    await channel.send(message)
