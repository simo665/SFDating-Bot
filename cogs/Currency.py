import discord
from discord import app_commands
from discord.ext import commands
import logging
import sqlite3
from datetime import datetime, timedelta
import random
import sys
import os
import aiohttp
from errors.error_logger import error_send

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.db_manager import DatabaseManager
from utilities.variables import get_emojis_variables
from utilities.shop_paginator import ShopPaginator
from utilities.gdrive_utils import get_drive_url, delete_drive_file

logger = logging.getLogger('bot.currency')

# Get custom emojis
emojis = get_emojis_variables()

# Define the main theme color (red)
THEME_COLOR = discord.Color.from_str("#c40000")

class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        
        # Initialize the database connection and create tables if they don't exist
        try:
            # Create database connection
            conn = sqlite3.connect('database/Currency.db')
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                last_daily TEXT,
                protected INTEGER DEFAULT 0
            )
            ''')
            
            # Create items table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                name TEXT,
                price INTEGER,
                description TEXT,
                type TEXT,
                role_id INTEGER,
                attachment_url TEXT,
                can_be_removed INTEGER DEFAULT 1,
                UNIQUE(server_id, name)
            )
            ''')
            
            # Create inventory table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id INTEGER,
                server_id INTEGER,
                FOREIGN KEY (item_id) REFERENCES items(id),
                UNIQUE(user_id, item_id, server_id)
            )
            ''')
            
            # Create default shop items
            default_items = [
                (0, "Dog", 500, "Barks when someone tries to rob you. 50% chance to catch thieves.", "protection", None, None, 0),
                (0, "Gun", 1000, "Scares off thieves. 80% chance to protect your money.", "protection", None, None, 0),
                (0, "Bank", 1500, "Store your SFlirts safely where they can't be stolen.", "storage", None, None, 0)
            ]
            
            cursor.execute("SELECT COUNT(*) FROM items WHERE server_id = 0")
            if cursor.fetchone()[0] < 3:  # If default items don't exist
                for item in default_items:
                    try:
                        cursor.execute('''
                        INSERT OR IGNORE INTO items 
                        (server_id, name, price, description, type, role_id, attachment_url, can_be_removed) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', item)
                    except sqlite3.IntegrityError:
                        pass  # Item already exists
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            print(e)
            
    # Helper methods
    async def create_embed(self, title, description, color=discord.Color.blue(), footer=None, fields=None, thumbnail=None):
        """Create a Discord embed"""
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        
        if footer:
            embed.set_footer(text=footer)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        if fields:
            for field in fields:
                embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', True))
        
        return embed
    
    # Money commands group
    money_group = app_commands.Group(name="money", description="View or manage your SFlirts")
    
    @money_group.command(name="show", description="View your or someone else's balance")
    @app_commands.describe(user="User to show balance (defaults to yourself)")
    async def money_show(self, interaction: discord.Interaction, user: discord.User = None):
        """Show balance command"""
        try:
            await self.show_balance(interaction, user or interaction.user)
        except Exception as e:
            await error_send(interaction)
            
    @money_group.command(name="give", description="Give SFlirts to another user")
    @app_commands.describe(
        user="User to give SFlirts to",
        amount="Amount of SFlirts to give"
    )
    async def money_give(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Give SFlirts to another user"""
        try:
            if amount <= 0:
                await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
                return
            
            if user.id == interaction.user.id:
                await interaction.response.send_message("You can't give SFlirts to yourself!", ephemeral=True)
                return
            
            success, message = self.db.transfer_money(interaction.user.id, user.id, amount)
            
            if success:
                embed = await self.create_embed(
                    title="SFlirts Transfer",
                    description=f"💸 {interaction.user.mention} gave {amount} SFlirts to {user.mention}!",
                    color=discord.Color.green()
                )
            else:
                embed = await self.create_embed(
                    title="Transfer Failed",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await error_send(interaction)
            
    @money_group.command(name="deposit", description="Deposit SFlirts to your bank")
    @app_commands.describe(amount="Amount of SFlirts to deposit")
    async def money_deposit(self, interaction: discord.Interaction, amount: int):
        """Deposit SFlirts to bank"""
        try:
            if amount <= 0:
                await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
                return
            
            success, message = self.db.deposit_to_bank(interaction.user.id, amount)
            
            if success:
                embed = await self.create_embed(
                    title="Bank Deposit",
                    description=message,
                    color=discord.Color.green()
                )
            else:
                embed = await self.create_embed(
                    title="Deposit Failed",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await error_send(interaction)
            
    @money_group.command(name="withdraw", description="Withdraw SFlirts from your bank")
    @app_commands.describe(amount="Amount of SFlirts to withdraw")
    async def money_withdraw(self, interaction: discord.Interaction, amount: int):
        """Withdraw SFlirts from bank"""
        try:
            if amount <= 0:
                await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
                return
            
            success, message = self.db.withdraw_from_bank(interaction.user.id, amount)
            
            if success:
                embed = await self.create_embed(
                    title="Bank Withdrawal",
                    description=message,
                    color=discord.Color.green()
                )
            else:
                embed = await self.create_embed(
                    title="Withdrawal Failed",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await error_send(interaction)
            
    @money_group.command(name="leaderboard", description="View the server's SFlirts leaderboard")
    async def money_leaderboard(self, interaction: discord.Interaction):
        """Show the server's leaderboard"""
        try:
            await self.show_leaderboard(interaction)
        except Exception as e:
            await error_send(interaction)
            
    async def show_balance(self, interaction: discord.Interaction, user: discord.User):
        """Show a user's balance"""
        try:
            user_data = self.db.get_user(user.id)
            
            if not user_data:
                await interaction.response.send_message("User not found in the database.", ephemeral=True)
                return
            
            # Get user's inventory to check for special items
            inventory = self.db.get_inventory(user.id, interaction.guild.id)
            item_names = [item['name'] for item in inventory]
            
            # Create special icons based on items owned
            icons = ""
            if "Dog" in item_names:
                icons += "🐕 "
            if "Gun" in item_names:
                icons += "🔫 "
            if "Bank" in item_names:
                icons += "🏦 "
            
            coin_emoji = emojis["sflirt_coin"]
            
            embed = await self.create_embed(
                title=f"{user.display_name}'s Balance {icons}",
                description=f"{emojis['redglassheart']} Here's the current balance for {user.mention}:",
                color=THEME_COLOR,
                thumbnail=user.display_avatar.url,
                fields=[
                    {"name": "💰 Wallet", "value": f"{user_data['balance']} {coin_emoji}", "inline": True},
                    {"name": "🏦 Bank", "value": f"{user_data['bank']} {coin_emoji}", "inline": True},
                    {"name": "💵 Total", "value": f"{user_data['balance'] + user_data['bank']} {coin_emoji}", "inline": True}
                ],
                footer=f"Use /money deposit or /money withdraw to manage your bank."
            )
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            await error_send(interaction)
            
    async def show_leaderboard(self, interaction: discord.Interaction):
        """Show the server's leaderboard"""
        try:
            leaderboard = self.db.get_leaderboard(interaction.guild.id)
            
            if not leaderboard:
                await interaction.response.send_message("No users found in the leaderboard yet.", ephemeral=True)
                return
            
            coin_emoji = emojis["sflirt_coin"]
            description = f"{emojis['Crown']} **SFlirts Leaderboard** {emojis['Crown']}\n\n"
            
            for i, user_data in enumerate(leaderboard, 1):
                user_id = user_data['user_id']
                try:
                    member = await interaction.guild.fetch_member(user_id)
                    username = member.display_name
                except:
                    username = f"User {user_id}"
                
                total = user_data['balance'] + user_data['bank']
                
                if i == 1:
                    medal = f"{emojis['redglassheart']}"
                elif i == 2:
                    medal = f"{emojis['PinkHearts']}"
                elif i == 3:
                    medal = f"{emojis['TwoHearts']}"
                else:
                    medal = f"{i}."
                
                description += f"{medal} **{username}**: {total} {coin_emoji}\n"
            
            embed = discord.Embed(
                title=f"{interaction.guild.name} - SFlirts Ranking",
                description=description,
                color=THEME_COLOR,
                timestamp=datetime.now()
            )
            
            embed.set_footer(text=f"Server: {interaction.guild.name} | Use /daily to earn daily rewards")
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            await error_send(interaction)
            
    @app_commands.command(name="daily", description="Claim your daily SFlirts reward")
    async def daily(self, interaction: discord.Interaction):
        """Claim daily reward"""
        try:
            success, message = self.db.daily_reward(interaction.user.id)
            
            if success:
                embed = await self.create_embed(
                    title="Daily Reward",
                    description=f"🎉 {message}",
                    color=discord.Color.green()
                )
            else:
                embed = await self.create_embed(
                    title="Daily Reward",
                    description=f"⏰ {message}",
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            await error_send(interaction)
            
    # Shop commands group
    shop_group = app_commands.Group(name="shop", description="Manage the server shop")
    
    @shop_group.command(name="show", description="View available shop items")
    async def shop_show(self, interaction: discord.Interaction):
        """Show the server shop"""
        try:
            await self.show_shop(interaction)
        except Exception as e:
            await error_send(interaction)
            
    @shop_group.command(name="add", description="Add an item to the server shop")
    @app_commands.describe(
        item_name="Name of the item",
        price="Price of the item in SFlirts",
        description="Description of the item",
        item_type="Type of item",
        role="Role to give when item is purchased (for role type)",
        attachment="Image attachment for the item (for attachment type)"
    )
    @app_commands.choices(item_type=[
        app_commands.Choice(name="Role", value="role"),
        app_commands.Choice(name="Attachment", value="attachment"),
        app_commands.Choice(name="Protection", value="protection"),
        app_commands.Choice(name="Storage", value="storage"),
        app_commands.Choice(name="Other", value="other")
    ])
    async def shop_add(self, interaction: discord.Interaction, 
                      item_name: str, price: int, 
                      description: str, item_type: str,
                      role: discord.Role = None,
                      attachment: discord.Attachment = None):
        """Add an item to the server shop"""
        try:
            # Check for admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions to manage the shop.", ephemeral=True)
                return
            
            if price <= 0:
                await interaction.response.send_message("Price must be greater than 0.", ephemeral=True)
                return
            
            # Validate inputs based on item type
            if item_type == "role" and not role:
                await interaction.response.send_message("You must specify a role for role-type items.", ephemeral=True)
                return
            
            if item_type == "attachment" and not attachment:
                await interaction.response.send_message("You must provide an attachment for attachment-type items.", ephemeral=True)
                return
            
            # Defer response since file upload might take time
            await interaction.response.defer(ephemeral=False, thinking=True)
            
            role_id = role.id if role else None
            attachment_url = None
            
            # Upload to Google Drive if it's an attachment item
            if attachment and item_type == "attachment":
                attachment_url = await get_drive_url(attachment, interaction.guild.id)
                if not attachment_url:
                    await interaction.followup.send("Failed to upload attachment to Google Drive. Please try again later.", ephemeral=True)
                    return
                logger.info(f"Uploaded attachment to Google Drive: {attachment_url}")
            elif attachment:
                # For non-attachment items, just use the Discord CDN URL
                attachment_url = attachment.url
            
            success, message = self.db.add_shop_item(
                interaction.guild.id, item_name, price, description, 
                item_type, role_id, attachment_url
            )
            
            if success:
                embed = await self.create_embed(
                    title=f"{emojis['Heartspin']} Item Added Successfully",
                    description=f"{emojis['TwoHearts']} **{item_name}** has been added to the shop!\n\n**Price:** {price} {emojis['sflirt_coin']}\n**Type:** {item_type.capitalize()}\n**Description:** {description}",
                    color=THEME_COLOR
                )
                
                if attachment:
                    embed.set_image(url=attachment.url)
                    
                if item_type == "attachment":
                    embed.add_field(name="📝 Note", value="When users buy this item, they will receive the attached file via DM.", inline=False)
                elif item_type == "role":
                    embed.add_field(name="📝 Note", value=f"When users buy this item, they will receive the {role.mention} role.", inline=False)
                    
                embed.set_footer(text=f"Added by {interaction.user.display_name} • Use /shop show to view the shop")
            else:
                embed = await self.create_embed(
                    title=f"{emojis['offline']} Failed to Add Item",
                    description=f"❌ {message}",
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await error_send(interaction)
            
    @shop_group.command(name="remove", description="Remove an item from the server shop")
    @app_commands.describe(item_name="Name of the item to remove")
    async def shop_remove(self, interaction: discord.Interaction, item_name: str):
        """Remove an item from the server shop"""
        try:
            # Check for admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions to manage the shop.", ephemeral=True)
                return
            
            success, message = self.db.remove_shop_item(interaction.guild.id, item_name)
            
            if success:
                embed = await self.create_embed(
                    title="Item Removed",
                    description=f"✅ {message}",
                    color=discord.Color.green()
                )
            else:
                embed = await self.create_embed(
                    title="Failed to Remove Item",
                    description=f"❌ {message}",
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await error_send(interaction)
            
    async def show_shop(self, interaction: discord.Interaction):
        """Show the server shop"""
        try:
            # Defer response since we're creating a paginated view
            await interaction.response.defer(ephemeral=False)
            
            items = self.db.get_shop_items(interaction.guild.id)
            
            if not items:
                embed = discord.Embed(
                    title=f"🛍️ {interaction.guild.name} Shop",
                    description=f"This server has no items to buy yet.\n\nAdmins can start adding items using `/shop add`.",
                    color=THEME_COLOR,
                    timestamp=datetime.now()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Get coin emoji
            coin_emoji = emojis["sflirt_coin"]
            
            # Create paginated shop view
            # Items per page 
            items_per_page = 7
            
            # Group by types but keep a flat list for pagination
            items_by_type = {}
            for item in items:
                item_type = item['type']
                if item_type not in items_by_type:
                    items_by_type[item_type] = []
                items_by_type[item_type].append(item)
                
            # Create embeds for each page
            embeds = []
            
            # First create type-specific pages
            for item_type, type_items in items_by_type.items():
                # Special icons for item types
                type_emoji = {
                    "role": emojis["Crown"],
                    "attachment": "📎",
                    "protection": "🛡️",
                    "storage": "💼",
                    "other": emojis["HeartPopUp"]
                }.get(item_type, emojis["HeartPopUp"])
                
                # Split type items into pages
                for i in range(0, len(type_items), items_per_page):
                    page_items = type_items[i:i + items_per_page]
                    
                    # Create embed for this page
                    embed = discord.Embed(
                        title=f"🛍️ {interaction.guild.name} Shop - {type_emoji} {item_type.capitalize()} Items",
                        description=f"{emojis['HeartMessage']} Use `/buy [item_name]` to purchase!",
                        color=THEME_COLOR,
                        timestamp=datetime.now()
                    )
                    
                    # Add each item to the embed
                    for item in page_items:
                        # Choose icon based on item name/type
                        item_icon = "💝"
                        if item['name'] == "Dog":
                            item_icon = emojis["CatHeart"]
                        elif item['name'] == "Gun":
                            item_icon = "🔫"
                        elif item['name'] == "Bank":
                            item_icon = "🏦"
                        elif item_type == "role":
                            item_icon = emojis["Crown"]
                        elif item_type == "attachment":
                            item_icon = "📎"
                        
                        # Create item field with formatted details
                        embed.add_field(
                            name=f"{item_icon} {item['name']}",
                            value=(
                                f"> {emojis['sflirt_coin']} **Price:** {item['price']} {coin_emoji}\n"
                                f"> {emojis['info']} **Description:** {item['description']}\n"
                                f"{emojis['line']}️"
                            ),
                            inline=False
                        )
                    
                    embed.set_footer(text=f"Page {len(embeds) + 1} • Use the buttons below to navigate")
                    embeds.append(embed)
            
            # If we have no embeds (unlikely), create one empty embed
            if not embeds:
                embed = discord.Embed(
                    title=f"🛍️ {interaction.guild.name} Shop",
                    description="No items available at this time.",
                    color=THEME_COLOR,
                    timestamp=datetime.now()
                )
                embeds.append(embed)
            
            # Create the paginator view
            view = ShopPaginator(embeds)
            message = await interaction.followup.send(embed=embeds[0], view=view)
            view.message = message
            
        except Exception as e:
            await error_send(interaction)
            
    @app_commands.command(name="buy", description="Buy an item from the shop")
    async def buy(self, interaction: discord.Interaction, item_name: str):
        """Buy an item from the shop"""
        try:
            # Defer response since we might need to send DMs
            await interaction.response.defer(ephemeral=False)
            
            success, message = self.db.buy_item(interaction.user.id, interaction.guild.id, item_name)
            
            if success:
                embed = await self.create_embed(
                    title=f"{emojis['Heartspin']} Purchase Successful!",
                    description=f"{emojis['TwoHearts']} {message}",
                    color=THEME_COLOR
                )
                
                # Check purchased item type and handle accordingly
                items = self.db.get_shop_items(interaction.guild.id)
                for item in items:
                    if item['name'].lower() == item_name.lower():
                        # If it's a role item, assign the role
                        if item['type'] == 'role' and item['role_id']:
                            try:
                                role = interaction.guild.get_role(item['role_id'])
                                if role:
                                    await interaction.user.add_roles(role)
                                    embed.add_field(
                                        name=f"{emojis['Crown']} Role Assigned",
                                        value=f"You've been given the {role.mention} role!",
                                        inline=False
                                    )
                            except Exception as role_error:
                                await error_send()
                                embed.add_field(
                                    name="⚠️ Role Error",
                                    value=f"Couldn't assign role: {role_error}",
                                    inline=False
                                )
                                
                        # If it's an attachment item, send DM with attachment link
                        elif item['type'] == 'attachment' and item['attachment_url']:
                            try:
                                # Create DM embed with attachment
                                dm_embed = discord.Embed(
                                    title=f"🎁 Your Purchase: {item['name']}",
                                    description=(
                                        f"Thank you for purchasing **{item['name']}**!\n\n"
                                        f"**Description:** {item['description']}\n\n"
                                        f"Here's your download link:"
                                    ),
                                    color=THEME_COLOR,
                                    timestamp=datetime.now()
                                )
                                
                                # Special formatting for Google Drive URLs
                                if "drive.google.com" in item['attachment_url']:
                                    dm_embed.add_field(
                                        name="📥 Download Link",
                                        value=f"[Click here to download]({item['attachment_url']})",
                                        inline=False
                                    )
                                else:
                                    dm_embed.add_field(
                                        name="📥 Download Link",
                                        value=item['attachment_url'],
                                        inline=False
                                    )
                                
                                dm_embed.set_footer(text=f"Purchased from {interaction.guild.name}")
                                
                                # Send DM to user
                                await interaction.user.send(embed=dm_embed)
                                embed.add_field(
                                    name="📩 Check Your DMs",
                                    value="I've sent you a direct message with your download!",
                                    inline=False
                                )
                            except Exception as dm_error:
                                await error_send()
                                embed.add_field(
                                    name="⚠️ DM Error",
                                    value="I couldn't send you a DM. Please make sure you have DMs enabled for this server.",
                                    inline=False
                                )
                            
                        # Set the transaction timestamp
                        embed.timestamp = datetime.now()
                        embed.set_footer(text=f"Purchase ID: {item['id']} • Thank you for your purchase!")
            else:
                embed = await self.create_embed(
                    title=f"{emojis['offline']} Purchase Failed",
                    description=f"❌ {message}",
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            await error_send(interaction)
            
    @app_commands.command(name="sell", description="Sell an item you own")
    async def sell(self, interaction: discord.Interaction, item_name: str):
        """Sell an item back to the shop"""
        try:
            success, message = self.db.sell_item(interaction.user.id, interaction.guild.id, item_name)
            
            if success:
                embed = await self.create_embed(
                    title="Item Sold",
                    description=f"✅ {message}",
                    color=discord.Color.green()
                )
                
                # Check if it's a role item and remove the role
                items = self.db.get_shop_items(interaction.guild.id)
                for item in items:
                    if item['name'].lower() == item_name.lower() and item['type'] == 'role' and item['role_id']:
                        try:
                            role = interaction.guild.get_role(item['role_id'])
                            if role and role in interaction.user.roles:
                                await interaction.user.remove_roles(role)
                                embed.description += f"\nThe {role.mention} role has been removed!"
                        except Exception as role_error:
                            await error_send()
                            embed.description += f"\nCouldn't remove role: {role_error}"
            else:
                embed = await self.create_embed(
                    title="Sale Failed",
                    description=f"❌ {message}",
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            await error_send(interaction)
            
            
    # Create an item command group
    item_group = app_commands.Group(name="item", description="Manage your inventory items")
    
    @item_group.command(name="use", description="Use an item from your inventory")
    async def item_use(self, interaction: discord.Interaction, item_name: str):
        """Use an item from your inventory"""
        try:
            # Defer response since we might need to send DMs
            await interaction.response.defer(ephemeral=False)
            
            # Check if user has the item
            user_inventory = self.db.get_inventory(interaction.user.id, interaction.guild.id)
            item_to_use = None
            
            for item in user_inventory:
                if item['name'].lower() == item_name.lower():
                    item_to_use = item
                    break
            
            if not item_to_use:
                embed = await self.create_embed(
                    title=f"{emojis['offline']} Item Not Found",
                    description=f"You don't have an item called '{item_name}' in your inventory.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Handle different item types
            if item_to_use['type'] == 'role' and item_to_use['role_id']:
                # Try to assign the role
                try:
                    role = interaction.guild.get_role(item_to_use['role_id'])
                    if not role:
                        embed = await self.create_embed(
                            title=f"{emojis['offline']} Role Not Found",
                            description=f"The role associated with this item no longer exists.",
                            color=discord.Color.red()
                        )
                        await interaction.followup.send(embed=embed)
                        return
                    
                    # Check if user already has the role
                    if role in interaction.user.roles:
                        embed = await self.create_embed(
                            title=f"{emojis['info']} Role Already Assigned",
                            description=f"You already have the {role.mention} role.",
                            color=THEME_COLOR
                        )
                        await interaction.followup.send(embed=embed)
                        return
                    
                    # Assign the role
                    await interaction.user.add_roles(role)
                    embed = await self.create_embed(
                        title=f"{emojis['Crown']} Role Assigned",
                        description=f"You've been given the {role.mention} role!",
                        color=THEME_COLOR
                    )
                    await interaction.followup.send(embed=embed)
                    
                except Exception as e:
                    await error_send()
                    embed = await self.create_embed(
                        title=f"{emojis['offline']} Role Assignment Failed",
                        description=f"Couldn't assign the role: {e}",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
            
            elif item_to_use['type'] == 'attachment' and item_to_use['attachment_url']:
                # Send item attachment in DM
                try:
                    # Create DM embed with attachment
                    dm_embed = discord.Embed(
                        title=f"🎁 Your Item: {item_to_use['name']}",
                        description=(
                            f"Here's your **{item_to_use['name']}** that you requested:\n\n"
                            f"**Description:** {item_to_use['description']}\n\n"
                            f"Here's your download link:"
                        ),
                        color=THEME_COLOR,
                        timestamp=datetime.now()
                    )
                    
                    # Special formatting for Google Drive URLs
                    if "drive.google.com" in item_to_use['attachment_url']:
                        dm_embed.add_field(
                            name="📥 Download Link",
                            value=f"[Click here to download]({item_to_use['attachment_url']})",
                            inline=False
                        )
                    else:
                        dm_embed.add_field(
                            name="📥 Download Link",
                            value=item_to_use['attachment_url'],
                            inline=False
                        )
                    
                    dm_embed.set_footer(text=f"From {interaction.guild.name}")
                    
                    # Send DM to user
                    await interaction.user.send(embed=dm_embed)
                    
                    embed = await self.create_embed(
                        title=f"{emojis['Heartspin']} Item Sent",
                        description="I've sent you a direct message with your item!",
                        color=THEME_COLOR
                    )
                    await interaction.followup.send(embed=embed)
                    
                except Exception as e:
                    await error_send()
                    embed = await self.create_embed(
                        title=f"{emojis['offline']} Couldn't Send DM",
                        description=f"I couldn't send you a DM. Please make sure you have DMs enabled for this server.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
            
            elif item_to_use['type'] == 'protection' or item_to_use['type'] == 'storage':
                # These are passive items that don't need to be actively used
                embed = await self.create_embed(
                    title=f"{emojis['info']} Passive Item",
                    description=f"**{item_to_use['name']}** is a passive item that's always active. You don't need to use it manually.",
                    color=THEME_COLOR
                )
                await interaction.followup.send(embed=embed)
                
            else:
                # Generic item use message for other types
                embed = await self.create_embed(
                    title=f"{emojis['HeartMessage']} Item Used",
                    description=f"You used **{item_to_use['name']}**!",
                    color=THEME_COLOR
                )
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await error_send(interaction)
            
            
    @item_group.command(name="sell", description="Sell an item from your inventory")
    async def item_sell(self, interaction: discord.Interaction, item_name: str):
        """Sell an item from your inventory (alias for /sell command)"""
        await self.sell(interaction, item_name)
    
    @item_group.command(name="list", description="View your inventory items")
    async def item_list_cmd(self, interaction: discord.Interaction, user: discord.User = None):
        await self.item_list(interaction, user)
        
    async def item_list(self, interaction: discord.Interaction, user: discord.User = None):
        """View your or another user's inventory"""
        try:
            target_user = user or interaction.user
            items = self.db.get_inventory(target_user.id, interaction.guild.id)
            
            if not items:
                await interaction.response.send_message(f"{target_user.display_name} doesn't have any items yet.", ephemeral=True)
                return
            
            # Group items by type
            item_groups = {}
            for item in items:
                item_type = item['type']
                if item_type not in item_groups:
                    item_groups[item_type] = []
                item_groups[item_type].append(item)
            
            # Get coin emoji
            coin_emoji = emojis["sflirt_coin"]
            
            # Create embed
            embed = discord.Embed(
                title=f"🎒 {target_user.display_name}'s Inventory",
                description=(
                    f"{emojis['FoxHi']} Items owned by {target_user.mention}:\n\n"
                    f"• Use `/item use [item_name]` to use an item\n"
                    f"• Use `/sell [item_name]` to sell an item"
                ),
                color=THEME_COLOR,
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Add fields for each type of item
            type_emojis = {
                "role": emojis["Crown"],
                "attachment": "📎",
                "protection": "🛡️",
                "storage": "💼",
                "other": emojis["HeartPopUp"]
            }
            
            for item_type, items_list in item_groups.items():
                emoji = type_emojis.get(item_type, emojis["HeartPopUp"])
                
                items_text = ""
                for item in items_list:
                    # Add icon based on item name for special items
                    special_icon = ""
                    if item['name'] == "Dog":
                        special_icon = emojis["CatHeart"] + " "
                    elif item['name'] == "Gun":
                        special_icon = "🔫 "
                    elif item['name'] == "Bank":
                        special_icon = "🏦 "
                    
                    # Get item ID for easier usage
                    item_id = item.get('id', 'N/A')
                    
                    items_text += f"**{special_icon}{item['name']}**\n"
                    items_text += f"┗ {item['description']}\n"
                    items_text += f"┗ Value: {int(item['price'] * 0.7)} {coin_emoji} (if sold)\n\n"
                
                if items_text:
                    embed.add_field(
                        name=f"{emoji} {item_type.capitalize()} Items",
                        value=items_text,
                        inline=False
                    )
            
            embed.set_footer(text="Inventory items")
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            await error_send(interaction)
            
    @app_commands.command(name="inventory", description="View your inventory")
    async def inventory(self, interaction: discord.Interaction, user: discord.User = None):
        """Alias for /item list command"""
        try:
            await self.item_list(interaction, user)
        except Exception:
            await error_send(interaction)
    
    @app_commands.command(name="steal", description="Try to steal SFlirts from another user")
    @app_commands.describe(user="The user to steal from")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hour cooldown
    async def steal(self, interaction: discord.Interaction, user: discord.User):
        """Try to steal SFlirts from another user"""
        try:
            if user.id == interaction.user.id:
                await interaction.response.send_message("You can't steal from yourself!", ephemeral=True)
                return
            
            if user.bot:
                await interaction.response.send_message("You can't steal from bots!", ephemeral=True)
                return
            
            # Check cooldown (handled by commands.cooldown decorator)
            
            success, message = self.db.attempt_steal(interaction.user.id, user.id)
            
            if success:
                embed = await self.create_embed(
                    title="Theft Successful!",
                    description=f"🦹‍♂️ {interaction.user.mention} {message} from {user.mention}",
                    color=discord.Color.green()
                )
            else:
                embed = await self.create_embed(
                    title="Theft Failed!",
                    description=f"🚨 {message}",
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            await error_send(interaction)
            
    # Help command group
    help_group = app_commands.Group(name="help", description="Get help with bot commands")
    
    @help_group.command(name="currency", description="Get help with SFlirts currency commands")
    async def help_currency(self, interaction: discord.Interaction):
        """Get help with currency commands"""
        try:
            coin_emoji = emojis["sflirt_coin"]
            
            embed = discord.Embed(
                title=f"{emojis['sflirt_coin']} SFlirts Currency Help",
                description=f"{emojis['PurpleHearts']} SFlirts is a fun currency system for your dating server. Here's how to use it!",
                color=THEME_COLOR,
                timestamp=datetime.now()
            )
            
            # Money commands
            embed.add_field(
                name=f"{emojis['sflirt_coin']} Currency Commands",
                value=(
                    f"**`/money show [user]`** - Show your balance or someone else's\n"
                    f"**`/money give [user] [amount]`** - Send {coin_emoji} to another user\n"
                    f"**`/money deposit [amount]`** - Deposit to your bank (requires Bank item)\n"
                    f"**`/money withdraw [amount]`** - Withdraw from your bank\n"
                    f"**`/money leaderboard`** - See the richest users\n"
                    f"**`/daily`** - Claim your daily {coin_emoji} reward\n"
                    f"**`/steal [user]`** - Try to steal {coin_emoji} from someone"
                ),
                inline=False
            )
            
            # Shop commands
            embed.add_field(
                name=f"{emojis['HeartPopUp']} Shop Commands",
                value=(
                    f"**`/shop show`** - View items available for purchase\n"
                    f"**`/buy [item_name]`** - Buy an item from the shop\n"
                    f"**`/sell [item_name]`** - Sell an item you own back to the shop\n"
                    f"**`/inventory [user]`** - View your inventory or someone else's"
                ),
                inline=False
            )
            
            # Item management commands
            embed.add_field(
                name=f"🎁 Item Commands",
                value=(
                    f"**`/item list [user]`** - View your inventory (same as /inventory)\n"
                    f"**`/item use [item_name]`** - Use an item from your inventory\n"
                    f"**`/item sell [item_name]`** - Sell an item (same as /sell)"
                ),
                inline=False
            )
            
            # Admin commands
            embed.add_field(
                name=f"{emojis['Crown']} Admin Shop Commands",
                value=(
                    f"**`/shop add [item_name] [price] [description] [item_type]`** - Add an item to the shop\n"
                    f" ┗ Supports role and attachment items\n"
                    f"**`/shop remove [item_name]`** - Remove an item from the shop"
                ),
                inline=False
            )
            
            # Protection items
            embed.add_field(
                name="🛡️ Default Protection Items",
                value=(
                    f"**{emojis['CatHeart']} Dog** (500 {coin_emoji}) - 50% chance to catch thieves\n"
                    f"**🔫 Gun** (1000 {coin_emoji}) - 80% chance to protect your money\n"
                    f"**🏦 Bank** (1500 {coin_emoji}) - Store your {coin_emoji} where they can't be stolen"
                ),
                inline=False
            )
            
            embed.set_footer(text="Use /help games to see available games to earn SFlirts")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await error_send(interaction)
            
async def setup(bot):
    await bot.add_cog(Currency(bot))
