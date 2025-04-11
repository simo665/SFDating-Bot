import discord 
from discord.ext import commands 
from discord import app_commands
from errors.error_logger import error_send 
from utilities import Permissions
from utilities.database import Database
from typing import List

class Thread(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.thread_channels = {}
        self.db = Database()
        self.bot.loop.create_task(self._modtable_())
        
    async def cog_unload(self):
        """No cleanup needed as Database class manages its own connections"""
        pass
        
    async def _modtable_(self):
        """Initialize the database table for threading"""
        await self.db.create_table("threading", """
            guild_id INTEGER PRIMARY KEY,
            thread_channel TEXT
        """)

    # auto threading 
    async def save_thread_channels(self, guild_id):
        """Save thread channel configuration to database"""
        await self.db.json_set(
            "threading", 
            "guild_id", 
            guild_id, 
            "thread_channel", 
            self.thread_channels.get(str(guild_id), {})
        )
            
    async def get_auto_thread_channels(self, guild_id):
        """Get thread channel configuration from database"""
        thread_channels = await self.db.get_auto_thread_channels(guild_id)
        self.thread_channels[str(guild_id)] = thread_channels
    
    async def check_perm(self, interaction, user_perms: List, bot_perms: List, target: discord.Member = None):
        permissions = Permissions(interaction)
        return await permissions.check_perm(user_perms, bot_perms, target)
    
    auto_group = app_commands.Group(name="auto", description="auto functionalities commands")
    thread = app_commands.Group(name="thread", description="auto threading commands", parent=auto_group)
    @thread.command(name="add", description="Create a thread for every message automatically.")
    async def auto_thread(self, interaction: discord.Interaction, channel: discord.TextChannel, thread_name: str, first_message: str = None, media_only: bool = False):
        try:
            authorized = await self.check_perm(interaction, ["administrator"], ["create_public_threads"])
            if not authorized:
                return 
            
            await self.get_auto_thread_channels(interaction.guild.id)
            thread_channel_config = {
                "name": thread_name,
                "first_message": first_message,
                "media_only": media_only
            }
            if str(interaction.guild.id) not in self.thread_channels:
                self.thread_channels[str(interaction.guild.id)] = {}
            self.thread_channels[str(interaction.guild.id)][str(channel.id)] = thread_channel_config
            await self.save_thread_channels(interaction.guild.id)
            await interaction.response.send_message(f"Auto-threading set up in {channel.mention} Successfully!")
            
        except Exception:
            await error_send(interaction)
            
    @thread.command(name="remove", description="Remove a thread for every message automatically.")
    async def remove_auto_thread(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            authorized = await self.check_perm(interaction, ["administrator"], ["create_public_threads"])
            if not authorized:
                return 
            await self.get_auto_thread_channels(interaction.guild.id)
            # Check if the channel exists in the stored thread channels
            guild_id = str(interaction.guild.id)
            if guild_id not in self.thread_channels or not self.thread_channels[guild_id]:
                return
            if str(channel.id) not in self.thread_channels[guild_id]:
                no_thread_embed = discord.Embed(
                    title="No Auto-threading Found", 
                    description=f"There is no auto-threading set up for {channel.mention}.", 
                    color=0xef214e
                )
                await interaction.followup.send(embed=no_thread_embed)
                return
            # Remove the channel from the thread configuration
            del self.thread_channels[guild_id][str(channel.id)]
            await self.save_thread_channels(interaction.guild.id)
            # Confirmation message
            await interaction.response.send_message(f"Auto-threading has been removed for {channel.mention} successfully!")
        except Exception:
            await error_send(interaction)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return 
        
        # Get command prefix
        prefixes = await self.bot.get_prefix(message)
        
        # Check if message starts with any of the prefixes
        if isinstance(prefixes, str):
            prefixes = [prefixes] 
        
        if any(message.content.startswith(prefix) for prefix in prefixes):
            await message.delete()
            
        guild_id = str(message.guild.id)
        try:
            await self.get_auto_thread_channels(message.guild.id)
            if guild_id not in self.thread_channels or not self.thread_channels[guild_id]:
                return
            if str(message.channel.id) not in self.thread_channels[guild_id]:
                return
            thread_name = self.thread_channels[guild_id][str(message.channel.id)].get("name", "")
            first_message = self.thread_channels[guild_id][str(message.channel.id)].get("first_message", "")
            media_only = self.thread_channels[guild_id][str(message.channel.id)].get("media_only", False)
            if media_only:
                if not message.attachments:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention} This channel is for media only, no text messages. Talk in the thread instead!", delete_after=8)
                    return 
            thread = await message.create_thread(
                name=thread_name if thread_name else "Public Thread", 
            )
            if first_message:
                await thread.send(first_message)
        except Exception:
            await error_send()

async def setup(bot):
    await bot.add_cog(Thread(bot))