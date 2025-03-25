import discord 
from discord.ext import commands 
from discord import app_commands
from errors.error_logger import error_send 
from utilities import Permissions
import sqlite3
from typing import List
import json 

class Thread(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.thread_channels = {}
        self.conn = sqlite3.connect("database/data.db")
        self._modtable_()
        
    def _modtable_(self):
        cur = self.conn.cursor()
        try:
            cur.execute("""CREATE TABLE IF NOT EXISTS threading(
                guild_id INTEGER PRIMARY KEY,
                thread_channel TEXT
            )""")
            self.conn.commit()
        finally:
            cur.close()

    # auto threading 
    def save_thread_channels(self, guild_id):
        cur = self.conn.cursor()
        try:
            thread_channels = json.dumps(self.thread_channels.get(str(guild_id), {}))
            cur.execute("""
                INSERT INTO threading (guild_id, thread_channel) 
                VALUES (?, ?) 
                ON CONFLICT(guild_id) DO UPDATE SET thread_channel = excluded.thread_channel
            """, (guild_id, thread_channels))
            self.conn.commit()
        finally:
            cur.close()
            
    def get_auto_thread_channels(self, guild_id):
        cur = self.conn.cursor()
        try:
            cur.execute("""
                SELECT thread_channel FROM threading
                WHERE guild_id = ?
            """, (guild_id,)
            )
            result = cur.fetchone()
            
            if result and result[0]:
                self.thread_channels[str(guild_id)] = json.loads(result[0]) 
            else:
                self.thread_channels[str(guild_id)] = {}  
                
        finally:
            cur.close()
    
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
            
            self.get_auto_thread_channels(interaction.guild.id)
            thread_channel_config = {
                "name": thread_name,
                "first_message": first_message,
                "media_only": media_only
            }
            if not str(interaction.guild.id) in self.thread_channels:
                self.thread_channels[str(interaction.guild.id)] = {}
            self.thread_channels[str(interaction.guild.id)][str(channel.id)] = thread_channel_config
            self.save_thread_channels(interaction.guild.id)
            await interaction.response.send_message(f"Auto-threading set up in {channel.mention} Successfully!")
            
        except Exception as e:
            await error_send(interaction)
            
    @thread.command(name="remove", description="Remove a thread for every message automatically.")
    async def remove_auto_thread(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            authorized = await self.check_perm(interaction, ["administrator"], ["create_public_threads"])
            if not authorized:
                return 
            self.get_auto_thread_channels(interaction.guild.id)
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
                response = await interaction.followup.send(embed=no_thread_embed)
                return
            # Remove the channel from the thread configuration
            del self.thread_channels[guild_id][str(channel.id)]
            self.save_thread_channels(interaction.guild.id)
            # Confirmation message
            await interaction.response.send_message(f"Auto-threading has been removed for {channel.mention} successfully!")
        except Exception as e:
            await error_send(interaction)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return 
        
        # Get command prefix
        prefixes = await self.bot.get_prefix(message)
        
        # Check if message starts with any of the prefixes
        if isinstance(prefixes, str):
            prefixes = [prefixes]  # Convert single prefix to a list
        
        if any(message.content.startswith(prefix) for prefix in prefixes):
            await message.delete()
            
        guild_id = str(message.guild.id)
        try:
            self.get_auto_thread_channels(message.guild.id)
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
                    await message.channel.send(f"{message.author.mention} This channel is fot media only, no text messages. Talk in the thread instead!", delete_after=8)
                    return 
            thread = await message.create_thread(
                name=thread_name if thread_name else "Public Thread", 
            )
            if first_message:
                await thread.send(first_message)
        except Exception as e:
            await error_send()

async def setup(bot):
    await bot.add_cog(Thread(bot))