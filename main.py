import discord
from discord.ext import commands
import asyncio
import os
import json
from dotenv import load_dotenv
from utilities import PersistentView
from utilities.database import Database
import traceback

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN2")

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.guilds = True
intents.message_content = True

prefix = "!"
bot = commands.Bot(command_prefix=prefix, intents=intents)

@bot.event 
async def on_ready():
    try:
        commands = await bot.tree.sync()
        db = Database()
        await db.init_database(bot)
        load_components()
        
        print("\n" + "="*50)
        print(f"Bot connected as: {bot.user}")
        print(f"Discord.py version: {discord.__version__}")
        print(f"Command prefix: {prefix}")
        print("="*50)
        
        print("\nREGISTERED COMMANDS:")
        print("-"*50)

        cog_commands = {}
        for cmd in commands:
            try:
                cog_name = getattr(cmd, "cog_name", None) or getattr(cmd, "module", None) or "No Category"
                if cog_name not in cog_commands:
                    cog_commands[cog_name] = []
                cog_commands[cog_name].append(cmd)
            except Exception as e:
                print(f"Error processing command {cmd}: {e}")
                continue

        for cog_name, cmds in sorted(cog_commands.items()):
            print(f"\n[{cog_name}]")
            for cmd in sorted(cmds, key=lambda x: getattr(x, "name", "")):
                cmd_description = getattr(cmd, "description", "No description")
                print(f"  /{getattr(cmd, 'name', 'unknown')} - {cmd_description}")
    
        std_commands = []
        try:
            std_commands = [cmd for cmd in bot.commands if not getattr(cmd, "hidden", False)]
        except Exception as e:
            print(f"Error processing standard commands: {e}")
            
        if std_commands:
            print("\n[Standard Commands]")
            for cmd in sorted(std_commands, key=lambda x: x.name):
                cmd_help = getattr(cmd, "help", None) or "No description"
                print(f"  {prefix}{cmd.name} - {cmd_help}")
        
        print("\n" + "-"*50)
        print(f"Total: {len(commands)} application commands, {len(std_commands)} standard commands")
        print(f"{bot.user} is now online and ready!")
        print("="*50 + "\n")
    except Exception as e:
        print(f"Error in on_ready: {e}")
        traceback.print_exc()
    
def load_components():
    for file in os.listdir("./templates"):
        try:
            if file.endswith(".json"):
                with open(f"./templates/{file}", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "components" in data and data["components"]:
                        bot.add_view(PersistentView(data["components"]))
        except Exception:
            print(f"Error loading file: {file}\n", "="*50)
            traceback.print_exc()
            print("="*50)

async def load_cogs():
    print("Loading cogs:")
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{file[:-3]}")
                print(f"  ✓ {file}")
            except Exception as e:
                print(f"  ✗ {file} - Error loading cog: {str(e)}")
                traceback.print_exc()
                continue  
    print("All cogs loaded successfully!\n")

async def main():
    try:
        async with bot:
            await load_cogs()
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("Bot has shut down.")
        os._exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        os._exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot has shut down.")
        os._exit(0)
    except Exception as e:
        print(f"Uncaught exception: {e}")
        traceback.print_exc()
        os._exit(1)