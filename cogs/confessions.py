import discord 
from discord.ext import commands
from discord import app_commands, Interaction, ui
from utilities import colors
from utilities import censor_text
from errors.error_logger import error_send
import sqlite3 
from datetime import datetime
from utilities import Permissions


class ConfessModal(ui.Modal, title="Anonymous Confession"):
    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect("database/data.db")
    
 
    def save_confession(self, message_id, user_id, content):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO confessions (message_id, user_id, content) VALUES (?, ?, ?)", (message_id, user_id, content))
            self.conn.commit()
        finally:
            cursor.close()
    
    confession = ui.TextInput(label="Your Confession", style=discord.TextStyle.paragraph, required=True, max_length=1000)

    async def on_submit(self, interaction: Interaction):
        try:
            await interaction.response.send_message("Thanks for your confession!", ephemeral=True)
            # Get the input and clean it
            text_input = self.confession.value
            cleaned_input = censor_text(text_input)
            # build the embed and send it in the channel 
            channel = interaction.channel
            embed = discord.Embed(
                title="🤐 New Confess",
                description=cleaned_input,
                color=colors.purple
            )
            view = ConfessButton()
            message = await channel.send(embed=embed, view=view)
            self.save_confession(message.id, interaction.user.id, text_input)
            thread = await message.create_thread(
                name="Comments",
                auto_archive_duration=1440
            )
        except Exception:
            await error_send(interaction)


class DeleteButton(ui.View):
    def __init__(self, message, reporter):
        super().__init__(timeout=None)
        self.message = message
        self.reporter = reporter
        self.response_embed = discord.Embed(title="Report Received – Thank You for Your Support", description="Thank you for your report. Our team has reviewed it and is taking the appropriate action. While we cannot disclose specific details regarding the outcome, we truly appreciate your effort in helping us maintain a safe and respectful community by reporting rule violations.", color=colors.primary)
        self.response_embed.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport5.png")
        self.response_embed.set_author(name=reporter.guild.name, url=f"https://discord.com/channels/{reporter.guild.id}", icon_url=reporter.guild.icon.url if reporter.guild.icon else None)
     
    
    @ui.button(label="Delete their message?", style=discord.ButtonStyle.red, custom_id="delete_message")
    async def delete_message(self, interaction: Interaction, button: discord.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            # Delete the message
            await self.message.delete()
            
            # Send a confirmation that the message has been deleted
            await interaction.followup.send("Message deleted!", ephemeral=True)
            
            # Disable the button after it is clicked and update the view
            button.disabled = True
            await interaction.message.edit(view=self)  # This will update the button state in the original message
            await self.reporter.send(embed=self.response_embed)
        except Exception:
            await error_send(interaction)
            
            
class ConfessButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.conn = sqlite3.connect("database/data.db")
    
    def get_confession_data(self, message_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT user_id, content FROM confessions WHERE message_id = ?", (message_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            
    @ui.button(label="Confess", style=discord.ButtonStyle.primary, custom_id="confess")
    async def confess(self, interaction: Interaction, button: discord.Button):
        modal = ConfessModal()
        await interaction.response.send_modal(modal)
        
    @ui.button(label="Report", style=discord.ButtonStyle.red, custom_id="report")
    async def Report(self, interaction: Interaction, button: discord.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            data = self.get_confession_data(interaction.message.id)
            user_id, content = data
            report_embed = discord.Embed(
                title="Reported Confess Message",
                description=f"""
🚹 **Reported by:** {interaction.user.mention}
🗨️ **Reported Message:**
> ==> {content}
💀 **Confess message author:** <@{user_id}>

**Note:**
> If they said something very inappropriate make sure to punish them and delete the message button below.
                """,
                color=colors.red
            )
            report_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            user = discord.utils.get(interaction.guild.members, id=user_id)
            if user:
                report_embed.set_thumbnail(url=user.display_avatar.url)
            report_embed.set_footer(text=user_id)
            report_embed.timestamp = datetime.utcnow()
            view = DeleteButton(interaction.message, interaction.user)
            channels_id = 0
            with open("./configs/channels/channels_id.json", "r") as f:
                data = json.load(f)
                channels_id = data.get(str(interaction.guild.id)).get("reports_channel_id")
            channel = discord.utils.get(interaction.guild.channels, id=channels_id)
            
            if channel:
                await channel.send(embed=report_embed, view=view)
            
            response_embed = discord.Embed(
                title="Reported successfully!",
                description=(
                    "Thank you for your report. Our moderation team has received the details and will review the situation and responsd shortly.\n\n"
                    "Please avoid engaging further with the reported user while we investigate. Your safety and the community’s well-being are our priority."
                ),
                color=colors.green
            )
            response_embed.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport4.png")
            await interaction.followup.send(embed=response_embed, ephemeral=True)
        except Exception:
            await error_send(interaction)

class Confessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("database/data.db")
        self.db_init()
    
    def db_init(self):
        cursor = self.conn.cursor()
        try: 
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS confessions (
                    message_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL
                )
            """)
            self.conn.commit()
        finally:
            cursor.close()
    
    # Confessions commands group 
    group = app_commands.Group(name="confessions", description="Confessions related commands")
    # start up command
    @group.command(name="start", description="Start and send confessions embed in a specific channel.")
    async def confessions_start(self, cmd: Interaction, channel: discord.TextChannel = None):
        try:
            has_permissions = await Permissions(cmd).check_guild_permission(cmd.user, ["administrator"])
            if not has_permissions:
                return 
            # Get channel 
            channel = channel if channel else cmd.channel
            # Create embed 
            embed = discord.Embed(
                title="Start a confession!",
                description="Do you have something to say in secret without people know that you who send it? Click the button below then.",
                color=colors.purple
            )
            # add view 
            view = ConfessButton()
            await cmd.response.send_message("Okay!", ephemeral=True)
            await channel.send(embed=embed, view=view)
        except Exception:
            await error_send(cmd)

async def setup(bot):
    cog = Confessions(bot)
    bot.add_view(ConfessButton())
    await bot.add_cog(cog)