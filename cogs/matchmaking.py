import discord
import random
import logging
import asyncio
import time
from discord.ext import commands
from discord import app_commands
import config
from utilities.role_parser import RoleParser
from utilities.matching_database import (
    get_user_preferences, update_user_preferences, add_match_history,
    get_recent_matches, update_last_match_time, get_active_pending_matches,
    block_user, opt_out_user, has_active_match, unmatch_users, 
    get_recently_declined_matches, get_excluded_matches
)
from utilities.utils2 import (
    OptOutView, UnmatchView, send_match_request, check_user_roles,
    create_match_embed, cleanup_task
)
from errors.error_logger import error_send


logger = logging.getLogger("./errors/errors.log")

class MatchmakingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_parser = RoleParser()

        # Schedule cleanup task
        self.cleanup_task = bot.loop.create_task(cleanup_task(bot))

    def cog_unload(self):
        # Cancel cleanup task on unload
        if self.cleanup_task:
            self.cleanup_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        """Load roles data when bot is ready"""
        logger.info("Matchmaking cog ready!")
        # Log roles data
        self.role_parser.load_roles()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Parse roles when joining a new guild"""
        logger.info(f"Parsing roles for new guild: {guild.name} (ID: {guild.id})")
        self.role_parser.parse_guild_roles(guild)

    match_group = app_commands.Group(name="match", description="Matchmaking commands")

    @match_group.command(name="find", description="Find the best match for you!")
    #@app_commands.checks.cooldown(1, config.MATCH_COMMAND_COOLDOWN)
    @app_commands.choices(
        partner_gender=[
            app_commands.Choice(name="♀️ Female", value="female"),
            app_commands.Choice(name="♂️ Male", value="male"),
            app_commands.Choice(name="🏳️‍⚧️ Trans Female", value="transfemale"),
            app_commands.Choice(name="🏳️‍⚧️ Trans Male", value="transmale"),
            app_commands.Choice(name="⚪ No Preference", value="none")
        ]
    )
    @app_commands.describe(partner_gender="What gender would you prefer your match to be?")
    async def find_match_cmd(self, interaction: discord.Interaction, partner_gender: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=False)
        try:
            await self.find_match(interaction, partner_gender)
        except Exception:
            await error_send(interaction)

    async def find_match(self, interaction: discord.Interaction, partner_gender):
        """Find the best match for the user"""
        # Check if command is used in the correct channel
        try:
            if interaction.channel.id not in config.MATCH_COMMAND_CHANNELS:
                embed = discord.Embed(
                    title="Wrong Channel",
                    description=f"This command can only be used in <#{config.MATCH_COMMAND_CHANNELS[0]}>",
                    color=config.Colors.ERROR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # First check if user already has an active match
            has_match, match_id, other_user_id = has_active_match(interaction.user.id)
            if has_match:
                try:
                    # Try to fetch the other user
                    other_user = await self.bot.fetch_user(other_user_id)

                    embed = discord.Embed(
                        title="You Already Have a Match",
                        description=f"You're already matched with {other_user.mention}! Would you like to unmatch and find someone new?",
                        color=config.Colors.WARNING
                    )

                    # Create unmatch view
                    from utilities.utils2 import UnmatchAndContinueView
                    view = UnmatchAndContinueView(
                        match_id=match_id, 
                        matched_user=other_user,
                        partner_gender=partner_gender.value
                    )

                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                    return
                except Exception as e:
                    logger.error(f"Error fetching matched user: {e}")
                    # Continue with the match search if we can't fetch the user

            # Check if the user has required roles
            has_required, missing_msg = check_user_roles(interaction.user, self.role_parser)
            if not has_required:
                embed = discord.Embed(
                    title="Missing Required Roles",
                    description=f"{missing_msg}\n\nPlease get the required roles from <#{config.ROLES_CHANNEL_ID}>.",
                    color=config.Colors.ERROR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Extract the user's data
            user_data = self.role_parser.extract_user_data(interaction.user)

            # Get matched role ID for the preferred gender
            guild = interaction.guild
            guild_roles = self.role_parser.get_guild_roles(guild)
            gender_role_ids = guild_roles.get("category_weights", {}).get("Gender", {}).get("roles")
            preferred_gender_role_id = gender_role_ids.get(partner_gender.value)

            if not preferred_gender_role_id:
                await interaction.followup.send(
                    f"Sorry, I couldn't find the role for {partner_gender.value} gender. Please try again later.",
                    ephemeral=True
                )
                return

            # Get the role object
            preferred_gender_role = discord.utils.get(guild.roles, id=preferred_gender_role_id)
            if not preferred_gender_role:
                await interaction.followup.send(
                    f"Sorry, I couldn't find the role for {partner_gender.value} gender. Please try again later.",
                    ephemeral=True
                )
                return

            # Find members with the preferred gender role
            match_candidates = []
            max_score = self.role_parser.get_max_score()

            # Get all excluded matches (declined, unmatched, etc.)
            excluded_users = get_excluded_matches(interaction.user.id, days=config.DECLINED_MATCHES_EXCLUSION_DAYS)

            for member in guild.members:
                # Skip bots, the user themselves, and members without the preferred gender role
                if member.bot or member == interaction.user or preferred_gender_role not in member.roles:
                    continue

                # Skip users with exclusion roles
                for role_type in config.EXCLUSION_ROLE_TYPES:
                    role_id = guild_roles.get("relationship_status", {}).get(role_type)
                    if role_id and discord.utils.get(member.roles, id=role_id):
                        continue

                # Skip users who have opted out
                if get_user_preferences(member.id).get("opt_out", False):
                    continue

                # Skip users who have DMs closed role
                dms_closed_role_id = guild_roles.get("dms_status", {}).get("dms closed")
                if dms_closed_role_id and discord.utils.get(member.roles, id=dms_closed_role_id):
                    continue

                # Skip users who are blocked by this user
                user_prefs = get_user_preferences(interaction.user.id)
                if str(member.id) in user_prefs.get("blocked_users", []):
                    continue

                # Skip users who have blocked this user
                member_prefs = get_user_preferences(member.id)
                if str(interaction.user.id) in member_prefs.get("blocked_users", []):
                    continue

                # Skip users who are in the exclusion list (declined, unmatched, etc.)
                if member.id in excluded_users:
                    logger.info(f"Skipping excluded match: {member.display_name} (ID: {member.id})")
                    continue

                # Extract member data
                member_data = self.role_parser.extract_user_data(member)

                # Compare users
                score = self.role_parser.compare_users(user_data, member_data)

                # Skip members with less than minimum threshold
                if score < config.MIN_MATCH_THRESHOLD:
                    continue

                # Add to candidates
                match_candidates.append((member, score, member_data))

            if not match_candidates:
                await interaction.followup.send(
                    "I couldn't find any matches for you at this time. Try again later or try different preferences.",
                    ephemeral=True
                )
                return

            # Sort candidates by score (highest first)
            match_candidates.sort(key=lambda x: x[1], reverse=True)

            # Get the best match (highest score)
            best_match, best_score, best_match_data = match_candidates[0]

            # Update the last match time
            update_last_match_time(interaction.user.id)

            # Create embed for match
            embed = create_match_embed(
                requester=interaction.user,
                target=best_match,
                score=best_score,
                max_score=max_score,
                user_data=best_match_data
            )

            # Send match to user 
            await interaction.followup.send(embed=embed, ephemeral=False)

            # Send match request to the target user
            success, match_id = await send_match_request(
                requester=interaction.user,
                target=best_match,
                score=best_score,
                max_score=max_score,
                user_data=user_data
            )

            if not success:
                # Add follow-up message that DM couldn't be sent
                embed = discord.Embed(
                    title="Match request failed",
                    description= "I tried to send a match request to this user, but they have DMs disabled. They won't receive your request.",
                    color=config.Colors.ERROR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="Request sent successfully!",
                    description=f"A match request sent to them! Please wait their response.\n\n! Match requests expire after 24 hours.",
                    color=config.Colors.SUCCESS
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception:
            await error_send(interaction)

    @match_group.command(name="opt_out", description="Opt out of the matchmaking system")
    async def opt_out(self, interaction: discord.Interaction):
        """Opt out of the matchmaking system"""
        await interaction.response.defer(ephemeral=True)

        # Check if user is already opted out
        preferences = get_user_preferences(interaction.user.id)
        if preferences.get("opt_out", False):
            embed = discord.Embed(
                title="Already Opted Out",
                description="You're already opted out of the matchmaking system.",
                color=config.Colors.INFO
            )

            # Create view with opt-in button
            view = discord.ui.View(timeout=60)

            async def opt_in_callback(btn_interaction):
                if btn_interaction.user.id != interaction.user.id:
                    await btn_interaction.response.send_message(
                        "This button is not for you.",
                        ephemeral=True
                    )
                    return

                await btn_interaction.response.defer(ephemeral=True)
                opt_out_user(interaction.user.id, False)
                await btn_interaction.followup.send(
                    "You have been opted back into the matchmaking system!",
                    ephemeral=True
                )

            opt_in_button = discord.ui.Button(
                label="Opt Back In", 
                style=discord.ButtonStyle.success
            )
            opt_in_button.callback = opt_in_callback
            view.add_item(opt_in_button)

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return

        # User is not opted out, ask for confirmation
        embed = discord.Embed(
            title="Opt Out of Matchmaking",
            description="Are you sure you want to opt out of matchmaking? You will no longer be suggested as a match to others.",
            color=config.Colors.WARNING
        )

        view = OptOutView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @match_group.command(name="unmatch", description="End your current match")
    async def unmatch(self, interaction: discord.Interaction):
        """Unmatch from your current match - immediately unmatch without confirmation"""
        await interaction.response.defer(ephemeral=True)

        # Check if user has an active match
        has_match, match_id, other_user_id = has_active_match(interaction.user.id)

        if not has_match:
            embed = discord.Embed(
                title="No Active Match",
                description="You don't have an active match to unmatch from.",
                color=config.Colors.INFO
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            # Fetch the other user
            other_user = await self.bot.fetch_user(other_user_id)
            
            # Directly unmatch without confirmation
            success, user_id, matched_user_id = unmatch_users(match_id)
            
            if success:
                # Create success embed
                embed = discord.Embed(
                    title="Unmatched Successfully",
                    description=f"You have been unmatched from {other_user.mention}. You are now free to match with others!",
                    color=config.Colors.SUCCESS
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Try to notify the other user via DM
                try:
                    embed = discord.Embed(
                        title="Match Update!",
                        description=f"{interaction.user.mention} has ended your match, it seems they don't know how amazing you're. lol,\nYou are now free to match with others.",
                        color=config.Colors.WARNING
                    )
                    await other_user.send(embed=embed)
                except discord.Forbidden:
                    # Can't send DM to the other user
                    pass
            else:
                embed = discord.Embed(
                    title="Unmatch Failed",
                    description="There was an error unmatching. Please try again later.",
                    color=config.Colors.ERROR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in unmatch command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while trying to unmatch. Please try again later.",
                color=config.Colors.ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @match_group.command(name="info", description="Get information about the matchmaking system")
    async def info(self, interaction: discord.Interaction):
        """Show information about the matchmaking system"""
        embed = discord.Embed(
            title="Matchmaking System Information",
            description="Here's how our matchmaking system works:",
            color=config.Colors.INFO
        )

        embed.add_field(
            name="Finding Matches",
            value="Use `/match find` to find your best match based on your roles.",
            inline=False
        )

        embed.add_field(
            name="Matching Algorithm",
            value="""
            Our system uses a point-based algorithm that considers:
            - Gender and sexuality compatibility
            - Age preferences
            - Height preferences
            - Regional preferences
            - Personality compatibility
            - Common hobbies and interests
            """,
            inline=False
        )

        embed.add_field(
            name="Cooldown",
            value=f"You can use the find match command once every {config.MATCH_COMMAND_COOLDOWN // 3600} hours.",
            inline=False
        )

        embed.add_field(
            name="Unmatching",
            value="Use `/match unmatch` if you want to end your current match and find someone new.",
            inline=False
        )

        embed.add_field(
            name="Opting Out",
            value="Use `/match opt_out` if you want to stop receiving match requests.",
            inline=False
        )

        embed.add_field(
            name="Declined Matches",
            value=f"If someone declines your match request, they won't appear in your matches for {config.DECLINED_MATCHES_EXCLUSION_DAYS} days.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MatchmakingCog(bot))