import discord 
from discord.ext import commands 
from discord import app_commands
from utilities import get_message_from_template, PersistentView
from errors.error_logger import error_send


class SelfRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
    
    self_group = app_commands.Group(name="self", description="Self related commands")
    roles_group = app_commands.Group(name="roles", description="roles related commands", parent=self_group)
    
    @roles_group.command(name="setup", description="setup self roles automatically")
    async def setuproles(self, interaction: discord.Interaction):
        try:
            
            message_data = get_message_from_template("selfroles_age")
            await interaction.response.send_message(message_data["content"], embeds=message_data["embeds"], view=message_data["view"])
            
            
        except Exception:
            await error_send(interaction)
        
async def setup(bot):
    await bot.add_cog(SelfRoles(bot))