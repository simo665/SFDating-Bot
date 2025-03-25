import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import time
import os
import json
from utilities import colors



class StickMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("database/data.db")
        self.stick_msgs = {}
        self.last_message_time = {}

        # Initialize database table
        self._initialize_database()

    # Database initialization
    def _initialize_database(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stick_messages(
                    guild_id INTEGER PRIMARY KEY,
                    stick_messages TEXT
                )
            """)
            self.conn.commit()
        finally:
            cursor.close()

    # Save stick messages to the database
    def _save_to_db(self, guild_id):
        cursor = self.conn.cursor()
        try:
            stick_messages_json = json.dumps(self.stick_msgs)
            cursor.execute("""
                INSERT OR REPLACE INTO stick_messages(guild_id, stick_messages)
                VALUES (?, ?)
            """, (guild_id, stick_messages_json))
            self.conn.commit()
        finally:
            cursor.close()

    # Load stick messages from the database
    def _load_from_db(self, guild_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT stick_messages FROM stick_messages WHERE guild_id = ?", (guild_id,))
            result = cursor.fetchone()
            if result:
                self.stick_msgs = json.loads(result[0])
            else:
                self.stick_msgs = {}
        finally:
            cursor.close()

    # Check if a channel is on cooldown
    def _is_on_cooldown(self, channel_id):
        current_time = time.time()
        last_time = self.last_message_time.get(channel_id, 0)
        cooldown_duration = 2  # seconds
        return (current_time - last_time) < cooldown_duration

    # Fetch the last bot message in the channel with the stick message content
    async def _get_last_bot_message(self, channel, stick_message):
        async for message in channel.history(limit=15):
            if message.author.id == self.bot.user.id and stick_message in message.embeds[0].description:
                return message
        return None

    # Process stick messages when a new message is sent
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        channel_id = message.channel.id
        self._load_from_db(guild_id)

        # Ignore channels without a stick message or if the channel is on cooldown
        if str(channel_id) not in self.stick_msgs or self._is_on_cooldown(channel_id):
            return

        stick_message = self.stick_msgs[str(channel_id)]
        if not stick_message:
            return

        # Delete the previous stick message
        last_stick_message = await self._get_last_bot_message(message.channel, stick_message)
        if last_stick_message:
            await last_stick_message.delete()

        # Send the new stick message
        embed = discord.Embed(description=stick_message, color=colors.primary)
        await message.channel.send(embed=embed)
        self.last_message_time[channel_id] = time.time()

    # Slash command to set a stick message
    stick_group = app_commands.Group(name="stick", description="Stick message-related commands")

    @stick_group.command(name="set", description="Set a stick message in a channel!")
    async def set_stick_message_slash_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.followup.send("You don't have permission to use this command!", ephemeral=True)
            return

        guild_id = channel.guild.id
        self._load_from_db(guild_id)

        # Set the stick message
        self.stick_msgs[str(channel.id)] = message
        self._save_to_db(guild_id)

        # Send the stick message to the channel
        embed = discord.Embed(description=message, color=colors.primary)
        await channel.send(embed=embed)
        await interaction.followup.send(f"A stick message has been set in {channel.mention} successfully!", ephemeral=True)

    # Slash command to remove a stick message
    @stick_group.command(name="remove", description="Remove a stick message from a channel!")
    async def remove_stick_message_slash_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.followup.send("You don't have permission to use this command!", ephemeral=True)
            return

        guild_id = channel.guild.id
        self._load_from_db(guild_id)

        if str(channel.id) in self.stick_msgs:
            stick_msg = self.stick_msgs[str(channel.id)]

            # Delete the last bot message containing the stick message
            last_stick_message = await self._get_last_bot_message(channel, stick_msg)
            if last_stick_message:
                await last_stick_message.delete()

            del self.stick_msgs[str(channel.id)]
            self._save_to_db(guild_id)
            await interaction.followup.send(f"Stick message in {channel.mention} has been removed successfully!", ephemeral=True)
        else:
            await interaction.followup.send(f"No stick message found in {channel.mention}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(StickMessage(bot))