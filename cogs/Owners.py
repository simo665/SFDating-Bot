import discord
from discord import app_commands
from discord.ext import commands
import logging
import random
from datetime import datetime
import sqlite3

# Set up logging
logger = logging.getLogger('bot.owner')

# Theme color for embeds
THEME_COLOR = discord.Color.from_rgb(196, 0, 0)  # #c40000

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        logger.info("Owner commands initialized")
    
    async def create_embed(self, title, description, color=discord.Color.blue(), footer=None, fields=None, thumbnail=None):
        """Create a Discord embed"""
        embed = discord.Embed(title=title, description=description, color=color or THEME_COLOR, timestamp=datetime.now())
        
        if footer:
            embed.set_footer(text=footer)
            
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        if fields:
            for field in fields:
                embed.add_field(name=field["name"], value=field["value"], inline=field.get("inline", False))
                
        return embed
        
    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        """Handle owner command errors"""
        if isinstance(error, app_commands.errors.CheckFailure):
            await interaction.response.send_message("⚠️ This command is only available to the bot owner.", ephemeral=True)
        else:
            logger.error(f"Error in owner command: {error}")
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
    
    async def is_owner(self, interaction: discord.Interaction) -> bool:
        """Check if the user is the bot owner"""
        owner_id = getattr(self.bot, 'owner_id', None)
        owner_ids = getattr(self.bot, 'owner_ids', set())
        is_owner = interaction.user.id == owner_id or interaction.user.id in owner_ids
        if is_owner:
            return True
        else:
            await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
            return False
    
    # Create a command group for owner commands
    owner_group = app_commands.Group(name="owner", description="Bot owner commands")
    @owner_group.command(name="add_money", description="[OWNER] Add SFlirts to a user")
    async def add_money(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Add SFlirts to a user's balance (owner only)"""
        try:
            is_owner = await self.is_owner(interaction)
            if not is_owner:
                return 
            # Check for valid amount
            if amount <= 0:
                await interaction.response.send_message("Amount must be positive", ephemeral=True)
                return
            
            # Get current balance
            user_data = self.db.get_user(user.id)
            current_balance = user_data.get('balance', 0)
            
            # Update the balance
            new_balance = self.db.update_balance(user.id, amount)
            
            # Create success embed
            embed = await self.create_embed(
                title="💰 Funds Added",
                description=f"Added {amount} SFlirts to {user.mention}'s balance.",
                color=discord.Color.green()
            )
            
            # Get updated user data
            updated_user = self.db.get_user(user.id)
            
            embed.add_field(
                name="Previous Balance",
                value=f"{current_balance} SFlirts",
                inline=True
            )
            
            embed.add_field(
                name="New Balance",
                value=f"{updated_user.get('balance', 0)} SFlirts",
                inline=True
            )
            
            if 'bank' in updated_user:
                embed.add_field(
                    name="Bank Balance",
                    value=f"{updated_user.get('bank', 0)} SFlirts",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error adding money: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    
    @owner_group.command(name="remove_money", description="[OWNER] Remove SFlirts from a user")
    async def remove_money(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Remove SFlirts from a user's balance (owner only)"""
        try:
            is_owner = await self.is_owner(interaction)
            if not is_owner:
                return 
            # Check for valid amount
            if amount <= 0:
                await interaction.response.send_message("Amount must be positive", ephemeral=True)
                return
            
            # Get current balance
            user_data = self.db.get_user(user.id)
            current_balance = user_data.get('balance', 0)
            
            # Don't allow removing more than the user has
            if amount > current_balance:
                amount = current_balance
            
            # Update the balance with a negative amount to remove
            new_balance = self.db.update_balance(user.id, -amount)
            
            # Create success embed
            embed = await self.create_embed(
                title="💸 Funds Removed",
                description=f"Removed {amount} SFlirts from {user.mention}'s balance.",
                color=discord.Color.red()
            )
            
            # Get updated user data
            updated_user = self.db.get_user(user.id)
            
            embed.add_field(
                name="Previous Balance",
                value=f"{current_balance} SFlirts",
                inline=True
            )
            
            embed.add_field(
                name="New Balance",
                value=f"{updated_user.get('balance', 0)} SFlirts",
                inline=True
            )
            
            if 'bank' in updated_user:
                embed.add_field(
                    name="Bank Balance",
                    value=f"{updated_user.get('bank', 0)} SFlirts",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error removing money: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    
    @owner_group.command(name="set_money", description="[OWNER] Set a user's SFlirts to a specific amount")
    async def set_money(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Set a user's balance to a specific amount (owner only)"""
        try:
            is_owner = await self.is_owner(interaction)
            if not is_owner:
                return 
            # Check for valid amount
            if amount < 0:
                await interaction.response.send_message("Amount cannot be negative", ephemeral=True)
                return
            
            # Get current user data
            user_data = self.db.get_user(user.id)
            current_balance = user_data.get('balance', 0)
            
            # Calculate the difference to add/remove
            difference = amount - current_balance
            
            # Use the update_balance method with the difference
            new_balance = self.db.update_balance(user.id, difference)
            
            # Create success embed
            embed = await self.create_embed(
                title="💰 Balance Set",
                description=f"Set {user.mention}'s balance to {amount} SFlirts.",
                color=discord.Color.blue()
            )
            
            # Get updated user data
            updated_user = self.db.get_user(user.id)
            
            embed.add_field(
                name="Previous Balance",
                value=f"{current_balance} SFlirts",
                inline=True
            )
            
            embed.add_field(
                name="New Balance",
                value=f"{updated_user.get('balance', 0)} SFlirts",
                inline=True
            )
            
            if 'bank' in updated_user:
                embed.add_field(
                    name="Bank Balance",
                    value=f"{updated_user.get('bank', 0)} SFlirts",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting money: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    
    @owner_group.command(name="reset_daily", description="[OWNER] Reset a user's daily cooldown")
    async def reset_daily(self, interaction: discord.Interaction, user: discord.User):
        """Reset a user's daily cooldown (owner only)"""
        try:
            is_owner = await self.is_owner(interaction)
            if not is_owner:
                return 
            # Reset last_daily to enable claiming again
            with self.db._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET last_daily = NULL WHERE user_id = ?", (user.id,))
                conn.commit()
            
            # Create success embed
            embed = await self.create_embed(
                title="⏰ Cooldown Reset",
                description=f"Reset daily cooldown for {user.mention}. They can now use the `/daily` command again.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error resetting daily cooldown: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    
    @owner_group.command(name="status", description="[OWNER] View bot status information")
    async def status(self, interaction: discord.Interaction):
        """View bot status information (owner only)"""
        try:
            is_owner = await self.is_owner(interaction)
            if not is_owner:
                return 
            # Gather basic stats
            total_users = 0
            total_guilds = len(self.bot.guilds)
            
            # Count total users across all guilds (remove duplicates)
            unique_users = set()
            for guild in self.bot.guilds:
                for member in guild.members:
                    unique_users.add(member.id)
            total_users = len(unique_users)
            
            # Count commands
            command_count = len(self.bot.tree.get_commands())
            
            # Get currency stats
            currency_stats = {}
            with self.db._connect() as conn:
                cursor = conn.cursor()
                # Total money in circulation
                cursor.execute("SELECT SUM(balance) + SUM(bank) FROM users")
                currency_stats['total_circulation'] = cursor.fetchone()[0] or 0
                
                # Richest user
                cursor.execute("SELECT user_id, balance + bank as total FROM users ORDER BY total DESC LIMIT 1")
                richest = cursor.fetchone()
                if richest:
                    richest_user_id = richest[0]
                    richest_amount = richest[1]
                    richest_user = self.bot.get_user(richest_user_id)
                    currency_stats['richest_user'] = f"{richest_user.name if richest_user else 'Unknown'} ({richest_amount} SFlirts)"
                else:
                    currency_stats['richest_user'] = "No users found"
                
                # Total users in database
                cursor.execute("SELECT COUNT(*) FROM users")
                currency_stats['db_users'] = cursor.fetchone()[0] or 0
            
            # Create embed with bot stats
            embed = await self.create_embed(
                title="🤖 Bot Status",
                description=f"Current status of {self.bot.user.name}",
                color=THEME_COLOR
            )
            
            # General stats
            embed.add_field(
                name="📊 General Stats",
                value=(
                    f"**Guilds:** {total_guilds}\n"
                    f"**Users:** {total_users}\n"
                    f"**Commands:** {command_count}\n"
                    f"**Latency:** {round(self.bot.latency * 1000)}ms"
                ),
                inline=False
            )
            
            # Currency stats
            embed.add_field(
                name="💰 Currency Stats",
                value=(
                    f"**Total Circulation:** {currency_stats['total_circulation']} SFlirts\n"
                    f"**Richest User:** {currency_stats['richest_user']}\n"
                    f"**Database Users:** {currency_stats['db_users']}"
                ),
                inline=False
            )
            
            # Set thumbnail to bot avatar
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing status: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Owner(bot))