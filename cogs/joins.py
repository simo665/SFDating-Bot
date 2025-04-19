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


class Joins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.welcome_channel = 1349150427106508821
        self.images = {
            1: "https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/gifs/GIF_20250324_052616_753.gif",
            2: "https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/gifs/w5.gif",
            3: "https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/gifs/w.gif",
            4: "https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/gifs/GIF_20250324_202406_009.gif"
        }
        self.next_image = 1
    
    def get_gif(self):
        gif = self.images[self.next_image]
        self.next_image += 1
        if self.next_image > len(self.images):
            self.next_image = 1
        return gif
    
    async def send_welcome_message(self, member):
        variables = get_member_variables(member)
        variables.update(get_emojis_variables())
        variables.update({"randomwelcomegif":self.get_gif()})
        data = get_message_from_template("joins_welcome", variables)
        channel = discord.utils.get(member.guild.text_channels, id=self.welcome_channel)
        await channel.send(data["content"], embeds=data["embeds"], view=data["view"])
    
    
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
            await error_send()  # Maybe pass `e` if useful for debugging
            return True
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            if member.bot:
                return
            is_new = await self.is_account_new(member)
            if is_new:
                return 
            await asyncio.sleep(3)
            await self.send_welcome_message(member)
        except Exception as e:
            print(e)
    
    joins = app_commands.Group(name="joins", description="Joins related commands.")
    welcome = app_commands.Group(name="welcome", description="welcome commands.", parent=joins)
    @welcome.command(name="test", description="Test welcome message")
    async def welcometest(self, interaction: discord.Interaction):
        try:
            await self.send_welcome_message(interaction.user)
            await interaction.response.send_message("Sent successfully!", ephemeral=True)
        except Exception:
            await error_send(interaction)

async def setup(bot):
    await bot.add_cog(Joins(bot))