import discord 
from discord.ext import commands
from discord import app_commands
from errors.error_logger import error_send

class DmManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.active_dms = {}
    
    # dm group 
    dm = app_commands.Group(name="dm", description="Dms related commands")
    
    # dm command 
    @dm.command(name="user", description="Send a dm message to a user")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def send_dm(self, interaction: discord.Interaction, user: discord.User, message: str):
        try:
            await interaction.response.defer(ephemeral=True)
            await user.send(message)
            await interaction.followup.send(f"Message sent to {user.mention} successfully!", ephemeral=True)
            
            self.active_dms[str(user.id)] = {
                "user2": interaction.user.id,
                "cmd_user": False
            }
            self.active_dms[str(interaction.user.id)] = {
                "user2": user.id,
                "cmd_user": True
            }
            
        except discord.Forbidden:
            await interaction.followup.send(f"Couldn't send a dm message to {user.mention}. Their dms probably closed", ephemeral=True)
        except Exception:
            await error_send(interaction)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if not isinstance(message.channel, discord.DMChannel):
            return 
        if message.author.bot:
            return 
        try:
            user = message.author
            user_id_str = str(user.id)
            # check if user in the active dms ir not
            if not user_id_str in self.active_dms:
                return 
            # check if the user 2 in active dms or not
            user2_id_str = str(self.active_dms.get(user_id_str).get("user2"))
            if not user2_id_str in self.active_dms:
                del self.active_dms[user_id_str]
                return 
            # check if it's matching the user id 
            if self.active_dms[user2_id_str].get("user2") != user.id:
                del self.active_dms[user_id_str]
                print(f"{user.id} != {self.active_dms[user2_id_str].get('user2')}")
                return 
            
            target_user = self.bot.get_user(self.active_dms[user_id_str].get("user2", 0))
            if not target_user:
                return 
            is_cmd_user = self.active_dms[user_id_str].get("cmd_user", False)
            if not is_cmd_user:
                await target_user.send(f"**{user.display_name}:** {message.content}\n-# {user.name}")
            else:
                await target_user.send(f"{message.content}")
        except Exception:
            await error_send()

async def setup(bot):
    cog = DmManager(bot)
    await bot.add_cog(cog)