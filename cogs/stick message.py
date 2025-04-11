import discord
from discord.ext import commands
from discord import app_commands
import time
from utilities import colors
from utilities.database import Database



class StickMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.stick_msgs = {}
        self.last_message_time = {}

        # Initialize database table
        self.bot.loop.create_task(self._initialize_database())

    # Database initialization
    async def _initialize_database(self):
        await self.db.create_table("stick_messages", """
            guild_id INTEGER PRIMARY KEY,
            stick_messages TEXT
        """)

    # Save stick messages to the database
    async def _save_to_db(self, guild_id):
        await self.db.json_set(
            "stick_messages", 
            "guild_id", 
            guild_id, 
            "stick_messages", 
            self.stick_msgs
        )

    # Load stick messages from the database
    async def _load_from_db(self, guild_id):
        data = await self.db.json_get(
            "stick_messages", 
            "guild_id", 
            guild_id, 
            "stick_messages"
        )
        self.stick_msgs = data or {}

    # Check if a channel is on cooldown
    def _is_on_cooldown(self, channel_id):
        current_time = time.time()
        last_time = self.last_message_time.get(channel_id, 0)
        cooldown_duration = 2  # seconds
        return (current_time - last_time) < cooldown_duration

    # Fetch the last bot message in the channel with the stick message content
    async def _get_last_bot_message(self, channel, stick_message):
        async for message in channel.history(limit=15):
            if message.author.id == self.bot.user.id and message.embeds and stick_message in message.embeds[0].description:
                return message
        return None

    # Process stick messages when a new message is sent
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        channel_id = message.channel.id
        await self._load_from_db(guild_id)

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
        await self._load_from_db(guild_id)

        # Set the stick message
        self.stick_msgs[str(channel.id)] = message
        await self._save_to_db(guild_id)

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
        await self._load_from_db(guild_id)

        if str(channel.id) in self.stick_msgs:
            stick_msg = self.stick_msgs[str(channel.id)]

            # Delete the last bot message containing the stick message
            last_stick_message = await self._get_last_bot_message(channel, stick_msg)
            if last_stick_message:
                await last_stick_message.delete()

            del self.stick_msgs[str(channel.id)]
            await self._save_to_db(guild_id)
            await interaction.followup.send(f"Stick message in {channel.mention} has been removed successfully!", ephemeral=True)
        else:
            await interaction.followup.send(f"No stick message found in {channel.mention}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(StickMessage(bot))