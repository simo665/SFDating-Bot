import discord 
from discord.ext import commands 
from discord import app_commands
from utilities import get_message_from_template
from utilities import get_member_variables, get_emojis_variables, get_all_variables
from errors.error_logger import error_send 
import asyncio 
import datetime
from utilities import colors
from utilities import send_log, get_account_age, format_time
import sqlite3
import random 

class Joins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.images = {
            1: {
                "gif": "https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/gifs/GIF_20250324_052616_753.gif",
                "color": 0xf18fa9
            },
            2: {
                "gif": "https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/gifs/w5.gif",
                "color": 0xb96855
            },
            3: {
                "gif": "https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/gifs/w.gif",
                "color": 0x22e4dd
            },
            4: {
                "gif": "https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/gifs/GIF_20250324_202406_009.gif",
                "color": 0xe0282b
            }
        }
        self.next_image = 1
        self.table_init()
    
    def table_init(self):
        con = sqlite3.connect("database/data.db")
        try:
            cur = con.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS welcome_channel (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
            """)
            con.commit()
        finally:
            con.close()
    
    def get_welcome_channel_id(self, guild_id):
        con = sqlite3.connect("database/data.db")
        try:
            cur = con.cursor()
            cur.execute("SELECT channel_id FROM welcome_channel WHERE guild_id = ?", (guild_id,))
            row = cur.fetchone()
        finally:
            con.close()
        return row[0] if row else None
    
    
    def get_gif(self):
        gif = self.images[self.next_image]["gif"]
        color = self.images[self.next_image]["color"]
        self.next_image += 1
        if self.next_image > len(self.images):
            self.next_image = 1
        return gif, color
    
    async def send_welcome_message(self, member):
        variables = get_member_variables(member)
        variables.update(get_emojis_variables())
        gif, color = self.get_gif()
        variables.update({"randomwelcomegif":gif})
        data = get_message_from_template("joins_welcome", variables)
        channel_id = self.get_welcome_channel_id(member.guild.id)
        if not channel_id:
            return  
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return 
        embed = data.get("embeds")[0]
        embed.color = color
        await channel.send(data["content"], embed=embed, view=data["view"])

    async def is_account_new(self, member):
        try: 
            min_age = 1
            
            variables = get_all_variables(member, member.guild, member)
            account_age = discord.utils.utcnow() - member.created_at
            created_at = get_account_age(member.created_at)
            
            if account_age < datetime.timedelta(days=min_age):
                img_embed = discord.Embed(color=colors.primary)
                img_embed.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport.jpg")
                
                time_remaining = datetime.timedelta(days=min_age) - account_age
                formated_time = format_time(time_remaining)
                embed = discord.Embed(
                    title="Your account is too young!",
                    description=f"Please wait until you're old enough to join our community.\nYou can join after {formated_time}\nlink: https://discord.gg/cA7sevJe4p",
                    color=colors.forbidden 
                )
                embed.set_footer(text="SFDating safety.")
                
                try:
                    await member.send(embeds=[img_embed, embed])
                except discord.Forbidden:
                    pass  
                try:
                    await member.kick(reason="Account age is too young.")
                except Exception as e:
                    variables.update({"reason": "I don't have permission to kick that member or they're higher than me."})
                    variables.update({"created_at": created_at})
                    await send_log(self.bot, variables, "log_new_account_failled_kick")
                    return True 
                variables.update({"reason": "Account is too young."})
                variables.update({"created_at": created_at})
                await send_log(self.bot, variables, "log_new_account_kick")
                return True 
            return False
        except Exception as e:
            await error_send() 
            return True
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            if member.bot:
                return
            is_new = False # await self.is_account_new(member)
            if is_new:
                return 
            await asyncio.sleep(3)
            await self.send_welcome_message(member)
        except Exception as e:
            print(e)
    
    joins = app_commands.Group(name="joins", description="Joins related commands.")
    welcome = app_commands.Group(name="welcome", description="welcome commands.", parent=joins)
    @welcome.command(name="test", description="Test welcome message")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcometest(self, interaction: discord.Interaction):
        try:
            await self.send_welcome_message(interaction.user)
            await interaction.response.send_message("Sent successfully!", ephemeral=True)
        except Exception:
            await error_send(interaction)
    
    @welcome.command(name="channel", description="Set the welcome channel for this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            con = sqlite3.connect("database/data.db")
            cur = con.cursor()
            cur.execute("""
            INSERT INTO welcome_channel (guild_id, channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id
            """, (interaction.guild.id, channel.id))
            con.commit()
            con.close()
            await interaction.response.send_message(f"Welcome channel set to {channel.mention}", ephemeral=True)
        except Exception:
            await error_send(interaction)
    

async def setup(bot):
    await bot.add_cog(Joins(bot))