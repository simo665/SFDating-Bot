import discord
from discord.ext import commands, tasks
import asyncio
import os
import json
import sys
import time
import traceback
import logging
from dotenv import load_dotenv
from utilities import PersistentView
from utilities.database import Database
from database_backup import upload_database
from utilities.matching_database import setup_database, check_pending_matches_table, cleanup_expired_matches
import config
from discord import app_commands
from utilities.utils2 import MatchAcceptView, OptOutView, UnmatchAndContinueView
from errors.error_logger import error_send
load_dotenv()
# Configure logging
logging.basicConfig(
    filename="errors/errors.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.ERROR
)
logger = logging.getLogger(__name__)

# Create database directory if it doesn't exist
database_dir = "database"
if not os.path.exists(database_dir):
    os.makedirs(database_dir)

# Set up intents
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

# Initialize the bot
prefix = "s!"
bot = commands.Bot(command_prefix=prefix, intents=intents)

# Define the automated match cleanup task
@tasks.loop(minutes=config.MATCH_CLEANUP_INTERVAL)
async def cleanup_matches_task():
    """Periodic task to clean up expired matches"""
    try:
        expired_count = cleanup_expired_matches()
    except Exception as e:
        await error_send()
# animated print
def _print(*args, sep=' ', end='\n', delay=0.001):
    text = sep.join(str(arg) for arg in args)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(end)
    sys.stdout.flush()

# Load configuration
def load_config():
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                return json.load(f)
        else:
            # Create default config if it doesn't exist
            default_config = {
                "guilds": {}
            }
            with open('config.json', 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
    except Exception as e:
        traceback.print_exc()
        return {"guilds": {}}
@bot.event
async def on_guild_join(guild):
    logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

    # Add guild to config if not present
    config_data = load_config()
    if str(guild.id) not in config_data["guilds"]:
        config_data["guilds"][str(guild.id)] = {
            "ticket_channel_id": None,
            "ticket_category_id": None,
            "ticket_log_channel_id": None,
            "staff_roles": []
        }
        with open('config.json', 'w') as f:
            json.dump(config_data, f, indent=4)

# when the bot starts
@bot.event
async def on_ready():
    try:
        os.system("clear")
        await load_all()
        await load_cogs()
        if os.getenv("SYNC_COMMANDS", "false").lower() == "true":
            commands = await bot.tree.sync()
        else:
            commands = bot.tree.get_commands()
        print("Done")
        matching_view()
        visualize(commands)
    except Exception as e:
        _print(f"Error in on_ready: {e}")
        traceback.print_exc()

# Function to load all the important things 
async def load_all():
    from database.db_manager import DatabaseManager
    # Initialize database manager and make it available to all cogs
    bot.db_manager = DatabaseManager()
        
    load_components()
    # Initialize database
    db = Database()
    await db.init_database(bot)
    # Make sure setup is complete
    setup_database()
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="lol! 💕"
    ))
    if not upload_backup.is_running():
        #upload_backup.start()
        pass
    if not cleanup_matches_task.is_running():
        cleanup_matches_task.start()

# matching view
def matching_view():
    bot.add_view(MatchAcceptView(match_id=None, target_user=None, requester_user=None, score=0, score_percentage=0))
    bot.add_view(OptOutView())
    bot.add_view(UnmatchAndContinueView(match_id=None, matched_user=None))

# Print loaded commands and infos for debugging 
def visualize(commands):
    _print("\n" + "="*50)
    _print(f"Bot connected as: {bot.user}")
    _print(f"Discord.py version: {discord.__version__}")
    _print(f"Command prefix: {prefix}")
    _print("="*50)
    
    # add matching views

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
    
# upload database backup
@tasks.loop(hours=1)
async def upload_backup():
    upload_database()

# Load templates components
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

# Load vbot cogs
async def load_cogs():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{file[:-3]}")
                _print(f"✓ {file}")
            except Exception:
                _print(f"X {file}")
                traceback.print_exc()
                exit(0)

# handle slash commands errors 
@bot.tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        # Calculate when the cooldown will end
        cooldown_end_timestamp = int(time.time() + error.retry_after)

        # Create an embed with better formatting
        embed = discord.Embed(
            title="❄️ Cooldown Active",
            description=f"You need to wait before using this command again.\n\n**Try again:** <t:{cooldown_end_timestamp}:R>\n**Available at:** <t:{cooldown_end_timestamp}:f>",
            color=config.Colors.WARNING
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
    elif isinstance(error, commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "💔 You don't have the required permissions to use this command.",
            ephemeral=True
        )
    else:
        await error_send()
        await interaction.response.send_message(
            "An error occurred while executing the command. Please try again later.",
            ephemeral=True
        )


if __name__ == "__main__":
    OWNER_ID = os.getenv("OWNER_ID")
    if OWNER_ID:
        try:
            # Convert to int or list of ints if comma-separated
            if "," in OWNER_ID:
                bot.owner_ids = set(int(id.strip()) for id in OWNER_ID.split(","))
            else:
                bot.owner_id = int(OWNER_ID)
        except ValueError:
            traceback.print_exc()
    try:
        # Load environment variables
        TOKEN = os.getenv("BOT_TOKEN") 
        if not TOKEN:
            print("No Discord token provided in environment variables")
            exit(0)
        bot.run(TOKEN)
    except KeyboardInterrupt:
        _print("Bot has shut down.")
        exit(0)
    except Exception as e:
        _print(f"Uncaught exception: {e}")
        traceback.print_exc()
        exit(1)