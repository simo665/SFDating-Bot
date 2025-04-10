import discord 
from discord.ext import commands 
from discord import app_commands
from utilities import get_message_from_template, PersistentView
from errors.error_logger import error_send
import asyncio


class SelfRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
    
    self_group = app_commands.Group(name="self", description="Self related commands")
    roles_group = app_commands.Group(name="roles", description="roles related commands", parent=self_group)
    
    @roles_group.command(name="setup", description="setup self roles automatically")
    async def setuproles(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        try:
            await interaction.response.send_message("Ok!", ephemeral=True)
            templates = [
                "selfroles_age", "selfroles_gender", "selfroles_sexuality", "selfroles_region", "selfroles_occupation", "selfroles_relationship", "selfroles_dms",
                "selfroles_age_preference", "selfroles_height", "selfroles_height_preference", "selfroles_distance", "selfroles_personality",
                "selfroles_personality_preference", "selfroles_hobbies", "selfroles_colors",
            ]
            channel = channel if channel else interaction.channel
            
            for template in templates:
                message_data = get_message_from_template(template)
                await channel.send(message_data["content"], embeds=message_data["embeds"], view=message_data["view"])
                #await asyncio.sleep(1)
            
        except Exception:
            await error_send(interaction)
        
async def setup(bot):
    await bot.add_cog(SelfRoles(bot))