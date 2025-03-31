import discord 
from discord import app_commands
from discord.ext import commands 
from utilities import Permissions, colors, get_message_from_dict
from utilities import get_message_from_template, get_emojis_variables
from errors.error_logger import error_send
from typing import List
import json
from utilities import get_all_variables
import re


class Send(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        
    async def check_perm(self, interaction, user_perms: List, bot_perms: List, target: discord.Member = None):
        permissions = Permissions(interaction)
        return await permissions.check_perm(user_perms, bot_perms, target)
 
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
            await interaction.response.send_message("Ok", ephemeral=True)
            await interaction.channel.send(content=message_data["content"], embeds=message_data["embeds"], view=message_data["view"])
            
        
        except Exception as e:
            await error_send(interaction)
    
    @send.command(name="message", description="Send a message using the bot.")
    @app_commands.describe(message="The message you want to send.", embed="Do you want to send it in embed?")
    @app_commands.choices(
        color = [
            app_commands.Choice(name="Pink", value=0xff4af0),
            app_commands.Choice(name="Blue", value=0x1299f0),
            app_commands.Choice(name="Green", value=0x08e508),
            app_commands.Choice(name="Red", value=0x08e508),
            app_commands.Choice(name="Yellow", value=0xdde508),
            app_commands.Choice(name="Orange", value=0xe57908),
            app_commands.Choice(name="Purple", value=0xac12ef)
        ]
    )
    async def send_message(self, interaction: discord.Interaction, message: str, embed: bool = False, embed_title: str = "", color: int = 0xff4af0):
        try:
            authorized = await self.check_perm(interaction, ["manage_messages"],[])
            if not authorized:
                return 
            await interaction.response.defer(ephemeral=True)
            await interaction.delete_original_response()
            
            permissions = interaction.channel.permissions_for(interaction.user)
            
            if embed:
                embed_response = discord.Embed(title=embed_title, description=message, color=color)
                await interaction.channel.send(embed=embed_response, allowed_mentions=discord.AllowedMentions.none())
            else:
                allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True) if not permissions.mention_everyone else discord.AllowedMentions(everyone=True, roles=True, users=True)
                await interaction.channel.send(message, allowed_mentions=allowed_mentions)
        except Exception as e:
            await error_send(interaction)
    
    
    
            
    @send.command(name="premium", description="Send premium info embed")
    async def premium_send(self, interaction: discord.Interaction):
        try:
            is_authorized = await self.check_perm(interaction, ["administrator"], ["embed_links"])
            if not is_authorized:
                return 
            variables = get_emojis_variables()
            data = get_message_from_template("premium_info", variables)
            await interaction.response.send_message(embeds=data["embeds"], view=data["view"])
        except Exception:
            await error_send(interaction)

async def setup(bot):
    await bot.add_cog(Send(bot))