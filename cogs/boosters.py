import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from errors.error_logger import error_send
import asyncio
from utilities import get_message_from_template, get_emojis_variables

CONFIG_FILE = 'boosters_config.json'

def load_config():
    return json.load(open(CONFIG_FILE)) if os.path.exists(CONFIG_FILE) else {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

class BoostersView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
        self.current_page = 0
        self.embeds = []
        
    
    async def update_embeds(self):
        """Generate fresh embeds based on current data"""
        cog = self.bot.get_cog("Boosters")
        if cog:
                self.embeds = await cog.build_embeds(str(self.guild_id))
                guild = discord.utils.get(self.bot.guilds, id=self.guild_id)
                await cog.update_board(guild)
        if not self.embeds:
            self.embeds = [discord.Embed(
                title="Error",
                description="Failed to load boosters",
                color=discord.Color.red()
            )]

    async def update_message(self, interaction: discord.Interaction):
        """Update message content while maintaining pagination"""
        await interaction.response.edit_message(
            embed=self.embeds[self.current_page],
            view=self
        )
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.send_message("There's no more embeds message duh 🙄 ", ephemeral=True)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            await self.update_message(interaction)
        else:
            await interaction.response.send_message("This is the final embed duh 🙄", ephemeral=True)



class Boosters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        
    
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            view = BoostersView(self.bot, guild.id)
            await view.update_embeds()
            self.bot.add_view(view)
            await asyncio.sleep(1)
           
    boosters_group = app_commands.Group(name="boosters", description="Boosters management")

    @boosters_group.command(name="setup")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Booster role to track",channel="Channel for the boosters board")
    async def setup_command(self, interaction: discord.Interaction, role: discord.Role, channel: discord.TextChannel):
        """Configure boosters board settings"""
        guild_id = str(interaction.guild_id)
        self.config[guild_id] = {
            "role_id": role.id,
            "channel_id": channel.id,
            "message_id": None
        }
        save_config(self.config)
        await interaction.response.send_message(
            f"Configuration saved!\nRole: {role.mention}\nChannel: {channel.mention}",
            ephemeral=True
        )

    @boosters_group.command(name="send")
    @app_commands.checks.has_permissions(administrator=True)
    async def send_board(self, interaction: discord.Interaction):
        """Create/update the boosters board"""
        guild_id = str(interaction.guild_id)
        if guild_id not in self.config:
            return await interaction.response.send_message(
                "Please run /boosters setup first!",
                ephemeral=True
            )
        
        config = self.config[guild_id]
        channel = self.bot.get_channel(config['channel_id'])
        
        # Generate embeds and view
        embeds = await self.build_embeds(guild_id)
        view = BoostersView(self.bot, guild_id)
        view.embeds = embeds
        
        # Update existing message or send new one
        message_id = config.get('message_id')
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embeds[0], view=view)
                return await interaction.response.send_message("Board updated!", ephemeral=True)
            except discord.NotFound:
                pass
        variables = get_emojis_variables()
        data = get_message_from_template("boosters_bored", variables)
        await channel.send(embed=data["embeds"][0])
        message = await channel.send(embed=embeds[0], view=view)
        self.config[guild_id]['message_id'] = message.id
        save_config(self.config)
        await interaction.response.send_message("Board created!", ephemeral=True)

    async def build_embeds(self, guild_id):
        """Create paginated boosters embeds"""
        config = self.config.get(guild_id, {})
        if not config.get('role_id'):
            return []
        
        guild = self.bot.get_guild(int(guild_id))
        role = guild.get_role(config['role_id'])
        if not role:
            return []
        
        # Format boosters list
        members = [f"<a:PinkHearts:1359829058942144594>・ {m.display_name} <a:redglassheart:1359831104995070183>" for m in role.members] or ["No boosters"]
        
        # Split into pages
        max_m = 25
        pages = [members[i:i+max_m] for i in range(0, len(members), max_m)]
        
        # Create embeds
        embeds = []
        variables = get_emojis_variables()
        data = get_message_from_template("boosters_bored", variables)
        for idx, page in enumerate(pages):
            # Create a new embed for each page
            template_embed = data["embeds"][1]
            embed = discord.Embed(
                title=template_embed.title,
                description="\n".join(page),
                color=template_embed.color
            )
            embed.set_footer(text=f"Page {idx+1}/{len(pages)}")
            # Copy other attributes if present (author, thumbnail, etc.)
            if template_embed.author:
                embed.set_author(name=template_embed.author.name, icon_url=template_embed.author.icon_url)
            if template_embed.thumbnail:
                embed.set_thumbnail(url=template_embed.thumbnail.url)
            # Add fields if needed
            for field in template_embed.fields:
                embed.add_field(name=field.name, value=field.value, inline=field.inline)
            embeds.append(embed)
        return embeds
        
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Update board when booster role changes"""
        guild_id = str(before.guild.id)
        if guild_id not in self.config:
            return
        
        config = self.config[guild_id]
        role = after.guild.get_role(config.get('role_id'))
        if not role:
            return
        
        # Check if booster role changed
        if (role in before.roles) != (role in after.roles):
            await self.update_board(after.guild)
            
    async def update_board(self, guild):
        """Update existing boosters board message while preserving pagination state"""
        config = self.config.get(str(guild.id))
        if not config or not config.get('message_id'):
            return
        
        channel = guild.get_channel(config['channel_id'])
        if not channel:
            return
        try:
            message = await channel.fetch_message(config['message_id'])
            embeds = await self.build_embeds(str(guild.id))
            
            # Get current page from existing embed footer
            current_page = 0
            if message.embeds and message.embeds[0].footer.text:
                footer_text = message.embeds[0].footer.text
                if 'Page' in footer_text:
                    current_page = int(footer_text.split('Page ')[1].split('/')[0]) - 1  # Convert to 0-based index
                    current_page = min(current_page, len(embeds) - 1)  # Clamp to valid range
            print(current_page)
            view = BoostersView(self.bot, guild.id)
            view.embeds = embeds
            view.current_page = current_page  # Preserve pagination state
            await message.edit(embed=embeds[current_page], view=view)
        except discord.NotFound:
            pass
        except Exception as e:
            await error_send()
    

async def setup(bot):
    # Ensure required intents are enabled
    if not bot.intents.members:
        raise ValueError("Member intents must be enabled for this cog to work properly")
    await bot.add_cog(Boosters(bot))