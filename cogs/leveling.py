import discord
from discord.ext import commands
from discord import app_commands
import random
import math
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from utilities.database import Database

class LevelingSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.xp_cooldown: Dict[int, datetime] = {}
        self.cooldown_time = 60
        self.min_xp = 15
        self.max_xp = 25
        self.bot.loop.create_task(self._init_db())
        
    async def _init_db(self):
        """Initialize the database tables for the leveling system"""
        await self.db.create_table("user_levels", """
            user_id INTEGER,
            guild_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            last_message TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        """)
        
        await self.db.create_table("level_settings", """
            guild_id INTEGER PRIMARY KEY,
            announcement_channel INTEGER,
            level_up_message TEXT,
            is_enabled BOOLEAN DEFAULT 1,
            xp_blacklist TEXT DEFAULT "[]"
        """)
    
    async def cog_unload(self):
        """Clean up any resources when the cog is unloaded"""
        pass
    
    def _calculate_level(self, xp: int) -> int:
        """Calculate the level based on XP
        
        This uses a logarithmic formula: level = 0.1 * sqrt(xp)
        """
        return int(0.1 * math.sqrt(xp))
    
    def _calculate_xp_for_level(self, level: int) -> int:
        """Calculate the XP needed for a specific level"""
        return int(100 * level * level)
    
    async def _add_xp(self, user_id: int, guild_id: int, xp_to_add: int) -> tuple:
        """Add XP to a user and check if they leveled up
        
        Returns:
            tuple: (new_level, old_level, total_xp)
        """
        user_data = await self.db.fetchone(
            "SELECT xp, level FROM user_levels WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        
        if user_data:
            current_xp = user_data["xp"]
            current_level = user_data["level"]
            new_xp = current_xp + xp_to_add
        else:
            current_xp, current_level = 0, 0
            new_xp = xp_to_add
            await self.db.insert(
                "user_levels",
                {
                    "user_id": user_id,
                    "guild_id": guild_id,
                    "xp": 0,
                    "level": 0,
                    "last_message": datetime.now().isoformat()
                }
            )
        
        new_level = self._calculate_level(new_xp)
        
        await self.db.update(
            "user_levels",
            {
                "xp": new_xp,
                "level": new_level,
                "last_message": datetime.now().isoformat()
            },
            "user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        
        return (new_level, current_level, new_xp)
    
    async def _get_leaderboard(self, guild_id: int, limit: int = 10) -> List:
        """Get the XP leaderboard for a guild"""
        return await self.db.fetchall(
            "SELECT user_id, xp, level FROM user_levels WHERE guild_id = ? ORDER BY xp DESC LIMIT ?",
            (guild_id, limit)
        )
    
    async def _is_in_cooldown(self, user_id: int) -> bool:
        """Check if user is in XP cooldown period"""
        if user_id in self.xp_cooldown:
            if datetime.now() < self.xp_cooldown[user_id]:
                return True
        return False
    
    async def _get_rank(self, user_id: int, guild_id: int) -> Optional[int]:
        """Get the rank of a user in the server"""
        ranks = await self.db.fetchall(
            "SELECT user_id FROM user_levels WHERE guild_id = ? ORDER BY xp DESC",
            (guild_id,)
        )
        
        for i, row in enumerate(ranks):
            if row['user_id'] == user_id:
                return i + 1
        return None
    
    async def _get_user_level(self, user_id: int, guild_id: int) -> tuple:
        """Get the level, XP, and rank of a user"""
        return await self.db.get_user_level(user_id, guild_id)
    
    async def _is_level_system_enabled(self, guild_id: int) -> bool:
        """Check if the leveling system is enabled for the guild"""
        result = await self.db.fetchone(
            "SELECT is_enabled FROM level_settings WHERE guild_id = ?",
            (guild_id,)
        )
        
        if result:
            return bool(result["is_enabled"])
        
        await self.db.insert(
            "level_settings",
            {"guild_id": guild_id, "is_enabled": 1}
        )
        return True
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Award XP when a user sends a message"""
        if message.author.bot or not message.guild:
            return
        
        if not await self._is_level_system_enabled(message.guild.id):
            return

        user_id = message.author.id
        if await self._is_in_cooldown(user_id):
            return
        
        xp_to_add = random.randint(self.min_xp, self.max_xp)
        
        new_level, old_level, _ = await self._add_xp(user_id, message.guild.id, xp_to_add)
        
        self.xp_cooldown[user_id] = datetime.now() + timedelta(seconds=self.cooldown_time)
        
        if new_level > old_level:
            await self._handle_level_up(message.author, message.guild, new_level)
    
    async def _handle_level_up(self, user: discord.Member, guild: discord.Guild, new_level: int):
        """Handle level-up events and send notifications"""
        settings = await self.db.fetchone(
            "SELECT announcement_channel, level_up_message FROM level_settings WHERE guild_id = ?",
            (guild.id,)
        )
        
        if not settings or not settings.get("announcement_channel"):
            channel_id = None
            level_up_message = "Congratulations {user_mention}! You've reached level **{level}**!"
        else:
            channel_id = settings["announcement_channel"]
            level_up_message = settings["level_up_message"] or "Congratulations {user_mention}! You've reached level **{level}**!"
        
        formatted_message = level_up_message.format(
            user_mention=user.mention,
            user_name=user.name,
            user_tag=user.discriminator,
            level=new_level
        )
        
        try:
            if channel_id:
                channel = guild.get_channel(channel_id)
                if channel and channel.permissions_for(guild.me).send_messages:
                    await channel.send(formatted_message)
            else:
                await user.send(f"**{guild.name}**: {formatted_message}")
        except discord.Forbidden:
            pass
    
    level_admin = app_commands.Group(name="leveladmin", description="Level system administration commands")
    
    @level_admin.command(name="setup", description="Configure the level system for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_level_system(
        self, 
        interaction: discord.Interaction, 
        channel: Optional[discord.TextChannel] = None,
        enabled: Optional[bool] = True
    ):
        """Configure the level system settings"""
        guild_id = interaction.guild.id
        
        settings_exist = await self.db.fetchone(
            "SELECT 1 FROM level_settings WHERE guild_id = ?",
            (guild_id,)
        )
        
        data = {"is_enabled": enabled}
        if channel:
            data["announcement_channel"] = channel.id
            
        if settings_exist:
            await self.db.update(
                "level_settings",
                data,
                "guild_id = ?",
                (guild_id,)
            )
        else:
            data["guild_id"] = guild_id
            await self.db.insert("level_settings", data)
        
        status = "enabled" if enabled else "disabled"
        channel_msg = f" with announcements in {channel.mention}" if channel else ""
        
        embed = discord.Embed(
            title="Level System Setup",
            description=f"Level system has been {status}{channel_msg}.",
            color=0xff4af0
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @level_admin.command(name="setmessage", description="Set the level up message format")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_level_message(self, interaction: discord.Interaction, message: str):
        """Set the level up message format
        
        Available variables:
        {user_mention} - Mentions the user
        {user_name} - The user's display name
        {user_tag} - The user's discriminator
        {level} - The new level number
        """
        guild_id = interaction.guild.id
        
        settings_exist = await self.db.fetchone(
            "SELECT 1 FROM level_settings WHERE guild_id = ?",
            (guild_id,)
        )
        
        if settings_exist:
            await self.db.update(
                "level_settings",
                {"level_up_message": message},
                "guild_id = ?",
                (guild_id,)
            )
        else:
            await self.db.insert(
                "level_settings",
                {"guild_id": guild_id, "level_up_message": message}
            )
        
        preview = message.format(
            user_mention=interaction.user.mention,
            user_name=interaction.user.name,
            user_tag=interaction.user.discriminator,
            level=10
        )
        
        embed = discord.Embed(
            title="Level Up Message Set",
            description=f"Level up message has been set.\n\n**Preview:**\n{preview}",
            color=0xff4af0
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @level_admin.command(name="reset", description="Reset XP and levels for a user or the entire server")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_levels(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ):
        """Reset XP for a specific user or the entire server"""
        guild_id = interaction.guild.id
        
        if user:
            await self.db.delete(
                "user_levels",
                "user_id = ? AND guild_id = ?",
                (user.id, guild_id)
            )
            message = f"Reset levels and XP for {user.mention}."
        else:
            await self.db.delete(
                "user_levels",
                "guild_id = ?",
                (guild_id,)
            )
            message = "Reset levels and XP for all users in this server."
        
        embed = discord.Embed(
            title="Level Reset",
            description=message,
            color=0xff4af0
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    level = app_commands.Group(name="level", description="Level system commands")
    
    @level.command(name="rank", description="Check your rank or another user's rank")
    async def check_rank(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ):
        """Check the rank of yourself or another user"""
        if not user:
            user = interaction.user
        
        guild_id = interaction.guild.id
        level, xp, rank = await self._get_user_level(user.id, guild_id)
        
        next_level_xp = self._calculate_xp_for_level(level + 1)
        current_level_xp = self._calculate_xp_for_level(level)
        xp_needed = next_level_xp - current_level_xp
        xp_progress = xp - current_level_xp
        progress_percentage = int((xp_progress / xp_needed) * 100) if xp_needed > 0 else 100
        
        filled = int(progress_percentage / 10)
        progress_bar = "⋆" + "•" * filled + "⋅" * (10 - filled) + "⋆"
        
        embed = discord.Embed(
            title=f"{user.display_name}'s Level",
            color=0xff4af0
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="Total XP", value=str(xp), inline=True)
        embed.add_field(name="Rank", value=f"#{rank}" if rank else "Unranked", inline=True)

        embed.add_field(
            name=f"Progress to Level {level + 1}",
            value=f"{progress_bar} {progress_percentage}%\n{xp_progress}/{xp_needed} XP",
            inline=False
        )
        
        embed.set_footer(text="⋆₊˚ XP is earned by chatting in the server ⋆₊˚")
        
        await interaction.response.send_message(embed=embed)
    
    @level.command(name="leaderboard", description="View the server's XP leaderboard")
    async def view_leaderboard(self, interaction: discord.Interaction, page: int = 1):
        """View the server's XP leaderboard"""
        guild_id = interaction.guild.id
        page = max(1, page)
        per_page = 10
        
        total_users = await self.db.fetchvalue(
            "SELECT COUNT(*) FROM user_levels WHERE guild_id = ?",
            (guild_id,)
        )
        
        max_page = math.ceil(total_users / per_page)
        page = min(page, max_page) if max_page > 0 else 1
        
        offset = (page - 1) * per_page
        leaderboard_data = await self._get_leaderboard(guild_id, limit=per_page)
        
        if not leaderboard_data:
            embed = discord.Embed(
                title="XP Leaderboard",
                description="No one has earned XP yet!",
                color=0xff4af0
            )
            await interaction.response.send_message(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"{interaction.guild.name} XP Leaderboard",
            color=0xff4af0
        )
        
        leaderboard_text = ""
        for index, entry in enumerate(leaderboard_data, start=offset + 1):
            user_id = entry["user_id"]
            xp = entry["xp"]
            level = entry["level"]
            
            member = interaction.guild.get_member(user_id)
            username = member.display_name if member else f"User {user_id}"
            
            if index == 1:
                medal = "🥇"
            elif index == 2:
                medal = "🥈"
            elif index == 3:
                medal = "🥉"
            else:
                medal = f"#{index}"
                
            leaderboard_text += f"{medal} **{username}** - Level {level} ({xp} XP)\n"
        
        embed.description = leaderboard_text
        embed.set_footer(text=f"Page {page}/{max_page} • Total Users: {total_users}")
        
        await interaction.response.send_message(embed=embed)
    
    @level.command(name="setxp", description="Set a user's XP (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_xp(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        xp: int
    ):
        """Set a user's XP to a specific amount (Admin only)"""
        if xp < 0:
            await interaction.response.send_message("XP cannot be negative.", ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        level = self._calculate_level(xp)
        
        await self.db.upsert(
            "user_levels", 
            {
                "user_id": user.id,
                "guild_id": guild_id,
                "xp": xp,
                "level": level,
                "last_message": datetime.now().isoformat()
            },
            ["user_id", "guild_id"]
        )
        
        embed = discord.Embed(
            title="XP Updated",
            description=f"Set {user.mention}'s XP to **{xp}** (Level **{level}**).",
            color=0xff4af0
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LevelingSystem(bot)) 