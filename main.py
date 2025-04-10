import discord
from discord.ext import commands
import asyncio
import os
import json
from dotenv import load_dotenv
from utilities import PersistentView
import traceback


databae_f = "database"
if not os.path.exists(databae_f):
    os.makedirs(databae_f)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.guilds = True
intents.message_content = True

prefix = "!"
bot = commands.Bot(command_prefix=prefix, intents=intents)

@bot.event 
async def on_ready():
    commands = await bot.tree.sync()
    load_components()
    print(f"{bot.user} is online with {len(commands)} commands!")
    
def load_components():
    for file in os.listdir("./templates"):
        try:
            if file.endswith(".json"):
                with open(f"./templates/{file}", "r") as f:
                    data = json.load(f)
                    if "components" in data and data["components"]:
                        bot.add_view(PersistentView(data["components"]))
        except Exception:
            print(f"Error loading file: {file}\n", "="*50)
            traceback.print_exc()
            print("="*50)

async def load_cogs():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{file[:-3]}")
            except Exception:
                traceback.print_exc()
                exit()
                
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)



asyncio.run(main())