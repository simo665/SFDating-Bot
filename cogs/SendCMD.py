import discord 
from discord import app_commands
from discord.ext import commands 
from utilities import Permissions, colors, get_message_from_dict
from errors.error_logger import error_send
from typing import List
import json
from utilities import get_all_variables

class Send(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def check_perm(self, interaction, user_perms: List, bot_perms: List, target: discord.Member = None):
        permissions = Permissions(interaction)
        is_user_has_perm = await permissions.check_guild_permission(interaction.user, user_perms)
        if not is_user_has_perm:
            return False 
        is_bot_has_perm = await permissions.check_guild_permission(interaction.guild.me, bot_perms)
        if not is_bot_has_perm:
            return False
        if target:
            against_roles = await permissions.check_mod_rules(target)
            if not against_roles:
                return False
        return True
    
    send = app_commands.Group(name="send", description="Send related commands.")
    @send.command(name="embed", description="Send a an embed.")
    @app_commands.describe(embed="Send an embed from a json code.")
    async def send_embed(self, interaction: discord.Interaction, embed: str):
        try:
            # check permissions 
            authorized = await self.check_perm(interaction, ["manage_messages"],[])
            if not authorized:
                return 
            data = None
            try: 
                data = json.loads(embed)
            except json.JSONDecodeError:
                embed = discord.Embed(title="Error", description="Invalid JSON format. Please provide a valid JSON.", color=colors.error)
                await interaction.response.send_message(embed=embed)
                return 
            member = interaction.user
            
            variables = get_all_variables(None, interaction.guild, member)
            variables.update({"reason": "/", "proofurl": ""})
            message_data = get_message_from_dict(data, variables)
            await interaction.response.send_message(content=message_data["content"], embeds=message_data["embeds"], view=message_data["view"])
        
        except Exception as e:
            await error_send(interaction)

async def setup(bot):
    await bot.add_cog(Send(bot))