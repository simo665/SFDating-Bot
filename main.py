import discord
from discord.ext import commands, tasks
import asyncio
import os
import json
from dotenv import load_dotenv
from utilities import PersistentView
from utilities.database import Database
import traceback
from database_backup import upload_database
import sys
import time


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

prefix = "s!"
bot = commands.Bot(command_prefix=prefix, intents=intents)


def _print(*args, sep=' ', end='\n', delay=0.005):
    text = sep.join(str(arg) for arg in args)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(end)
    sys.stdout.flush()
    
@bot.event 
async def on_ready():
    try:
        commands = await bot.tree.sync()
        db = Database()
        await db.init_database(bot)
        load_components()
        
        _print("\n" + "="*50)
        _print(f"Bot connected as: {bot.user}")
        _print(f"Discord.py version: {discord.__version__}")
        _print(f"Command prefix: {prefix}")
        _print("="*50)
        
        _print("\nREGISTERED COMMANDS:")
        _print("-"*50)

        cog_commands = {}
        for cmd in commands:
            try:
                cog_name = getattr(cmd, "cog_name", None) or getattr(cmd, "module", None) or "No Category"
                if cog_name not in cog_commands:
                    cog_commands[cog_name] = []
                cog_commands[cog_name].append(cmd)
            except Exception as e:
                _print(f"Error processing command {cmd}: {e}")
                continue

        for cog_name, cmds in sorted(cog_commands.items()):
            _print(f"\n[{cog_name}]")
            for cmd in sorted(cmds, key=lambda x: getattr(x, "name", "")):
                cmd_description = getattr(cmd, "description", "No description")
                _print(f"  /{getattr(cmd, 'name', 'unknown')} - {cmd_description}")
    
        std_commands = []
        try:
            std_commands = [cmd for cmd in bot.commands if not getattr(cmd, "hidden", False)]
        except Exception as e:
            _print(f"Error processing standard commands: {e}")
            
        if std_commands:
            _print("\n[Standard Commands]")
            for cmd in sorted(std_commands, key=lambda x: x.name):
                cmd_help = getattr(cmd, "help", None) or "No description"
                _print(f"  {prefix}{cmd.name} - {cmd_help}")
        
        _print("\n" + "-"*50)
        _print(f"Total: {len(commands)} application commands, {len(std_commands)} standard commands")
        _print(f"{bot.user} is now online and ready!")
        _print("="*50 + "\n")
        
        
        #upload_backup.start()
    except Exception as e:
        _print(f"Error in on_ready: {e}")
        traceback.print_exc()

@tasks.loop(hours=1)
async def upload_backup():
    upload_database()
    
def load_components():
    for file in os.listdir("./templates"):
        try:
            if file.endswith(".json"):
                with open(f"./templates/{file}", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "components" in data and data["components"]:
                        bot.add_view(PersistentView(data["components"]))
        except Exception:
            _print(f"Error loading file: {file}\n", "="*50)
            traceback.print_exc()
            _print("="*50)

async def load_cogs(selected_cogs=None):
    """Load cogs specified in selected_cogs or all if None."""
    _print("Loading cogs:")
    if selected_cogs:
        _print("Loading selected cogs:", ", ".join(selected_cogs))
        for cog in selected_cogs:
            try:
                # Load the cog by name (without .py)
                await bot.load_extension(f"cogs.{cog}")
                _print(f"  ✓ {cog}.py")
            except Exception as e:
                _print(f"  ✗ {cog}.py - Error loading cog: {str(e)}\n\n", "="*50,"\n\n")
                traceback.print_exc()
                os._exit(1)
    else:
        # Original behavior: load all cogs
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                try:
                    await bot.load_extension(f"cogs.{file[:-3]}")
                    _print(f"  ✓ {file}")
                except Exception as e:
                    _print(f"  ✗ {file} - Error loading cog: {str(e)}")
                    traceback.print_exc()
                    os._exit(1)
    _print("All cogs loaded successfully!\n")

async def main():
    try:
        async with bot:
            # Get cog names from command-line arguments (exclude script name)
            args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
            selected_cogs = args if args else None  # Use args if provided
            await load_cogs(selected_cogs)
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        _print("Bot has shut down.")
        os._exit(0)
    except Exception as e:
        _print(f"Fatal error: {e}")
        traceback.print_exc()
        os._exit(1)



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _print("Bot has shut down.")
        os._exit(0)
    except Exception as e:
        _print(f"Uncaught exception: {e}")
        traceback.print_exc()
        os._exit(1)
        
