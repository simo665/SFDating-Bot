import discord 
from discord.ext import commands 
from discord import app_commands
from utilities import get_message_from_template
from utilities import get_member_variables, get_emojis_variables
from errors.error_logger import error_send 
import asyncio 

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
    
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return 
        await asyncio.sleep(3)
        await self.send_welcome_message(member)
    
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