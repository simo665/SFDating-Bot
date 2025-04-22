import discord
from discord import app_commands
from discord.ext import commands, tasks
from mcstatus import JavaServer, BedrockServer
import asyncio
import json
import os
from utilities import get_emojis_variables

class ServerStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_message = None
        self.channel_id = None
        self.message_id = None
        self.update_status.start()
        self.bot.loop.create_task(self.restore_message())
        self.emojis = get_emojis_variables()

    def cog_unload(self):
        self.update_status.cancel()

    def save_status_info(self):
        if self.channel_id and self.status_message:
            data = {
                "channel_id": self.channel_id,
                "message_id": self.status_message.id
            }
            with open("server_status.json", "w") as f:
                json.dump(data, f)

    def load_status_info(self):
        if os.path.exists("server_status.json"):
            with open("server_status.json", "r") as f:
                data = json.load(f)
                self.channel_id = data.get("channel_id")
                self.message_id = data.get("message_id")
                return True
        return False

    async def restore_message(self):
        await self.bot.wait_until_ready()
        if self.load_status_info():
            try:
                channel = self.bot.get_channel(self.channel_id)
                if channel:
                    msg = await channel.fetch_message(self.message_id)
                    self.status_message = msg
            except Exception as e:
                print(f"Couldn't fetch saved status message: {e}")

    async def get_status_embed(self):
        java_ip = "mc.convolutionary.dev"
        bedrock_ip = "mc.convolutionary.dev"
        java_port = 25565
        bedrock_port = 19132

        java_status = "Offline"
        bedrock_status = "Offline"
        java_players = "N/A"
        bedrock_players = "N/A"

        try:
            java_server = JavaServer.lookup(f"{java_ip}:{java_port}")
            java_status_response = java_server.status()
            java_status = "Online"
            java_players = f"{java_status_response.players.online}/{java_status_response.players.max}"
        except:
            pass

        try:
            bedrock_server = BedrockServer.lookup(f"{bedrock_ip}:{bedrock_port}")
            bedrock_status_response = bedrock_server.status()
            bedrock_status = "Online"
            bedrock_players = f"{bedrock_status_response.players_online}/{bedrock_status_response.players_max}"
        except:
            pass
        
        status_emoji = self.emojis.get("online") if "Online" in (java_status, bedrock_status) else self.emojis.get("offline")
        
        embed = discord.Embed(
            title=f"SFDating Minecraft Server",
            color=discord.Color.green() if "Online" in (java_status, bedrock_status) else discord.Color.red()
        )
        
        bedrock_status_emoji = self.emojis.get("online") if "Online" == bedrock_status else self.emojis.get("offline")
        java_status_emoji = self.emojis.get("online") if "Online" == java_status else self.emojis.get("offline")

        embed.add_field(name="Java Edition", value=(
            f"> {self.emojis.get('emoji_id')} **IP:** `{java_ip}`\n"
            f"> {bedrock_status_emoji} **Status:** {java_status}\n"
        ), inline=False)
        
        embed.add_field(name="Bedrock Edition", value=(
            f"> {self.emojis.get('emoji_id')} **IP:** `{bedrock_ip}`\n"
            f"> {bedrock_status_emoji} **Status:** {bedrock_status}\n"
        ), inline=False)
        
        embed.add_field(name=f"Players playing", value=(
            f"> {self.emojis['emoji_member']} **Total Players:** {java_players}\n"
            f"> {self.emojis['emoji_member']} **Bedrock Players:** {bedrock_players}"
        ), inline=False)
        

        embed.add_field(name="Server provider", value="Server was provided by <@1178440413212844102> with 6gb ram up to 60gb if needed. Thanks ❤️")

        embed.set_footer(text="Auto-updates every 10 seconds")
        return embed

    @app_commands.command(name="mcserver", description="Show Minecraft server status (auto-updates)")
    async def mcserver(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = await self.get_status_embed()
        msg = await interaction.channel.send(embed=embed)
        self.status_message = msg
        self.channel_id = interaction.channel.id
        self.save_status_info()
        await interaction.followup.send("Done 👍")

    @tasks.loop(seconds=10)
    async def update_status(self):
        if self.status_message and self.channel_id:
            try:
                channel = self.bot.get_channel(self.channel_id)
                if channel:
                    embed = await self.get_status_embed()
                    await self.status_message.edit(embed=embed)
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"Error updating message: {e}")

async def setup(bot):
    await bot.add_cog(ServerStatus(bot))