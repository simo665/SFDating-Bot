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
    get_recently_declined_matches, get_excluded_matches,
    get_all_active_matches, get_match_limit
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
    @app_commands.checks.cooldown(3, config.MATCH_COMMAND_COOLDOWN)
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
        except Exception as e:
            logger.error(f"Error in find_match_cmd: {e}")
            await error_send(interaction, error_text=f"An error occurred: {str(e)}")

    async def find_match(self, interaction: discord.Interaction, partner_gender):
        """Find the best match for the user"""
        # Check if command is used in the correct channel
        try:
            if interaction.channel.id not in config.MATCH_COMMAND_CHANNELS:
                embed = discord.Embed(
                    title="Wrong Channel",
                    description=f"This command can only be used in the matching channel.",
                    color=config.Colors.ERROR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # First check if user already has an active match
            # Get all active matches for the user
            active_matches = get_all_active_matches(interaction.user.id)
            
            # Get the user's match limit based on their roles
            match_limit = get_match_limit(interaction.user)
            
            # Check if user has reached their match limit
            if len(active_matches) > 0:
                # If match limit is 0, it means unlimited matches
                if match_limit > 0 and len(active_matches) >= match_limit:
                    # Get user's match status
                    try:
                        from utilities.utils2 import get_user_match_status
                        match_status = await get_user_match_status(interaction.user)
                        
                        # Generate list of current matches
                        # First make sure we have a deduplicated list
                        unique_matches = {}
                        for match in active_matches:
                            # Only keep the most recent match for each user
                            if match['other_user_id'] not in unique_matches:
                                unique_matches[match['other_user_id']] = match
                        
                        # Generate the list from our deduplicated dictionary
                        matched_users_text = ""
                        for i, (other_user_id, match) in enumerate(list(unique_matches.items())[:5], 1):  # Show up to 5 matches
                            try:
                                matched_user = await self.bot.fetch_user(other_user_id)
                                matched_users_text += f"{i}. {matched_user.mention}\n"
                            except Exception:
                                matched_users_text += f"{i}. User ID: {other_user_id}\n"
                        
                        # Show ellipsis if there are more matches than we're displaying
                        if len(unique_matches) > 5:
                            matched_users_text += f"...and {len(unique_matches) - 5} more.\n"
                        
                        embed = discord.Embed(
                            title="Match Limit Reached",
                            description=f"{match_status['formatted_status']}\n\nYou need to unmatch with someone before finding a new match.",
                            color=config.Colors.WARNING
                        )
                        
                        # Add current matches
                        embed.add_field(
                            name="Your Current Matches",
                            value=matched_users_text,
                            inline=False
                        )
                        
                        # Add instructions
                        embed.add_field(
                            name="What Next?",
                            value="Use `/match unmatch` to end one of your current matches before finding a new one.",
                            inline=False
                        )
                        
                        # Include info about premium/booster perks
                        if match_limit == config.DEFAULT_MATCH_LIMIT:
                            premium_text = f"💎 **Want more matches?**\nServer Boosters: {config.BOOSTER_MATCH_LIMIT} matches\nPremium Users: Unlimited matches"
                            embed.add_field(
                                name="Upgrade Options",
                                value=premium_text,
                                inline=False
                            )
                            
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
                    except Exception as e:
                        logger.error(f"Error displaying match limit message: {e}")
                        await error_send(interaction, error_text=f"Error displaying your matches: {str(e)}")
                
                # If we're here, the user hasn't reached their match limit, so we proceed
                # Let's show them their current match status
                if len(active_matches) > 0:
                    # Get user's match status
                    from utilities.utils2 import get_user_match_status
                    match_status = await get_user_match_status(interaction.user)
                    
                    # Make sure we have a deduplicated list
                    unique_matches = {}
                    for match in active_matches:
                        # Only keep the most recent match for each user
                        if match['other_user_id'] not in unique_matches:
                            unique_matches[match['other_user_id']] = match
                    
                    # Get usernames of current matches (up to 3)
                    matched_users_text = ""
                    for i, (other_user_id, match) in enumerate(list(unique_matches.items())[:3], 1):
                        try:
                            matched_user = await self.bot.fetch_user(other_user_id)
                            matched_users_text += f"{matched_user.mention}, "
                        except:
                            matched_users_text += f"User {other_user_id}, "
                    
                    # Remove trailing comma and space
                    if matched_users_text:
                        matched_users_text = matched_users_text[:-2]
                    
                    # Create embed with match status
                    embed = discord.Embed(
                        title="Your Current Matches",
                        description=match_status["formatted_status"],
                        color=config.Colors.INFO
                    )
                    
                    # Format based on number of matches
                    if len(unique_matches) == 1:
                        matched_with_text = f"You're currently matched with {matched_users_text}."
                    else:
                        matched_with_text = f"You're currently matched with {matched_users_text}"
                        if len(unique_matches) > 3:
                            matched_with_text += f" and {len(unique_matches) - 3} others."
                        else:
                            matched_with_text += "."
                    
                    embed.add_field(
                        name="Your Active Matches", 
                        value=matched_with_text,
                        inline=False
                    )
                    
                    embed.add_field(
                        name="Finding New Match",
                        value="Proceeding to look for a new match for you...",
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
            
                # We don't return here - allow the user to continue matching

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
            
            # Get users that are already matched with this user
            already_matched_users = []
            active_matches = get_all_active_matches(interaction.user.id)
            for match in active_matches:
                already_matched_users.append(match['other_user_id'])
            
            # Add currently matched users to the exclusion list
            if already_matched_users:
                logger.info(f"Adding {len(already_matched_users)} already matched users to exclusion list")
                excluded_users.extend(already_matched_users)

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

                # Skip users who are in the exclusion list (declined, unmatched, already matched, etc.)
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

        except Exception as e:
            logger.error(f"Error in find_match command: {e}")
            await error_send(interaction, error_text=f"An error occurred during matching: {str(e)}")

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

    @match_group.command(name="unmatch", description="End your current match(es)")
    async def unmatch(self, interaction: discord.Interaction):
        """Unmatch from your current match(es) - immediately unmatch without confirmation"""
        await interaction.response.defer(ephemeral=True)

        # Get all active matches
        active_matches = get_all_active_matches(interaction.user.id)

        if not active_matches:
            embed = discord.Embed(
                title="No Active Matches",
                description="You don't have any active matches to unmatch from.",
                color=config.Colors.INFO
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # If there's only one match, just unmatch directly
        if len(active_matches) == 1:
            match = active_matches[0]
            match_id = match['match_id']
            other_user_id = match['other_user_id']
            
            try:
                # Fetch the other user
                other_user = await self.bot.fetch_user(other_user_id)

                # Directly unmatch without confirmation
                success, user_id, matched_user_id = unmatch_users(match_id)

                if success:
                    # Get updated match status
                    from utilities.utils2 import get_user_match_status
                    match_status = await get_user_match_status(interaction.user)
                    
                    # Create success embed
                    embed = discord.Embed(
                        title="Unmatched Successfully",
                        description=f"You have been unmatched from {other_user.mention}. You are now free to match with others!",
                        color=config.Colors.SUCCESS
                    )
                    
                    # Add match status field
                    embed.add_field(
                        name="Your Match Status",
                        value=match_status["formatted_status"],
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)

                    # Try to notify the other user via DM
                    try:
                        embed = discord.Embed(
                            title="Match Update!",
                            description=f"{interaction.user.mention} has ended your match. You are now free to match with others.",
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
        else:
            # If there are multiple matches, create a select menu to choose which one to unmatch from
            class UnmatchSelect(discord.ui.Select):
                def __init__(self, matches, bot):
                    self.matches = matches
                    self.bot = bot
                    options = []
                    
                    for i, match in enumerate(matches):
                        try:
                            user_name = f"User {match['other_user_id']}"
                            try:
                                user = bot.get_user(match['other_user_id'])
                                if user:
                                    user_name = user.display_name
                            except:
                                pass
                            
                            options.append(discord.SelectOption(
                                label=f"Unmatch from {user_name}",
                                description=f"Match ID: {match['match_id']}",
                                value=str(i)
                            ))
                        except Exception as e:
                            logger.error(f"Error creating unmatch option: {e}")
                    
                    # Add option to unmatch from all
                    options.append(discord.SelectOption(
                        label="Unmatch from ALL matches",
                        description="This will end all your current matches",
                        value="all"
                    ))
                    
                    super().__init__(placeholder="Select a match to unmatch from...", options=options)
                
                async def callback(self, select_interaction):
                    if select_interaction.user.id != interaction.user.id:
                        await select_interaction.response.send_message("This menu is not for you.", ephemeral=True)
                        return
                    
                    await select_interaction.response.defer(ephemeral=True)
                    
                    if self.values[0] == "all":
                        # Unmatch from all matches
                        success_count = 0
                        fail_count = 0
                        
                        for match in self.matches:
                            try:
                                success, _, _ = unmatch_users(match['match_id'])
                                if success:
                                    success_count += 1
                                    # Try to notify the other user
                                    try:
                                        other_user = await self.bot.fetch_user(match['other_user_id'])
                                        embed = discord.Embed(
                                            title="Match Update!",
                                            description=f"{interaction.user.mention} has ended your match. You are now free to match with others.",
                                            color=config.Colors.WARNING
                                        )
                                        await other_user.send(embed=embed)
                                    except:
                                        pass
                                else:
                                    fail_count += 1
                            except Exception as e:
                                logger.error(f"Error unmatching multiple users: {e}")
                                fail_count += 1
                        
                        # Send results
                        if success_count > 0:
                            # Get updated match status
                            from utilities.utils2 import get_user_match_status
                            match_status = await get_user_match_status(select_interaction.user)
                            
                            embed = discord.Embed(
                                title="Unmatched Successfully",
                                description=f"You have been unmatched from {success_count} connections.",
                                color=config.Colors.SUCCESS
                            )
                            if fail_count > 0:
                                embed.description += f"\n\nFailed to unmatch from {fail_count} connections."
                            
                            # Add updated match status field
                            embed.add_field(
                                name="Your Match Status",
                                value=match_status["formatted_status"],
                                inline=False
                            )
                            
                            await select_interaction.followup.send(embed=embed, ephemeral=True)
                        else:
                            embed = discord.Embed(
                                title="Unmatch Failed",
                                description="Failed to unmatch from any connections.",
                                color=config.Colors.ERROR
                            )
                            await select_interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        # Unmatch from the selected match
                        match_index = int(self.values[0])
                        if match_index < len(self.matches):
                            match = self.matches[match_index]
                            match_id = match['match_id']
                            other_user_id = match['other_user_id']
                            
                            try:
                                # Get the other user
                                other_user = await self.bot.fetch_user(other_user_id)
                                
                                # Unmatch
                                success, _, _ = unmatch_users(match_id)
                                
                                if success:
                                    # Get updated match status
                                    from utilities.utils2 import get_user_match_status
                                    match_status = await get_user_match_status(select_interaction.user)
                                    
                                    embed = discord.Embed(
                                        title="Unmatched Successfully",
                                        description=f"You have been unmatched from {other_user.mention}.",
                                        color=config.Colors.SUCCESS
                                    )
                                    
                                    # Add updated match status field
                                    embed.add_field(
                                        name="Your Match Status",
                                        value=match_status["formatted_status"],
                                        inline=False
                                    )
                                    
                                    await select_interaction.followup.send(embed=embed, ephemeral=True)
                                    
                                    # Notify the other user
                                    try:
                                        embed = discord.Embed(
                                            title="Match Update!",
                                            description=f"{interaction.user.mention} has ended your match. You are now free to match with others.",
                                            color=config.Colors.WARNING
                                        )
                                        await other_user.send(embed=embed)
                                    except:
                                        pass
                                else:
                                    embed = discord.Embed(
                                        title="Unmatch Failed",
                                        description="There was an error unmatching. Please try again later.",
                                        color=config.Colors.ERROR
                                    )
                                    await select_interaction.followup.send(embed=embed, ephemeral=True)
                            except Exception as e:
                                logger.error(f"Error in unmatch selection: {e}")
                                embed = discord.Embed(
                                    title="Error",
                                    description="An error occurred while trying to unmatch. Please try again later.",
                                    color=config.Colors.ERROR
                                )
                                await select_interaction.followup.send(embed=embed, ephemeral=True)
            
            # Get user's match status
            from utilities.utils2 import get_user_match_status
            match_status = await get_user_match_status(interaction.user)
            
            # Create the select view
            view = discord.ui.View(timeout=60)
            view.add_item(UnmatchSelect(active_matches, self.bot))
            
            embed = discord.Embed(
                title="Select Match to Unmatch From",
                description=f"Please select which match you want to unmatch from, or choose to unmatch from all.",
                color=config.Colors.INFO
            )
            
            # Add match status field
            embed.add_field(
                name="Your Match Status",
                value=match_status["formatted_status"],
                inline=False
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @match_group.command(name="info", description="Get information about the matchmaking system")
    async def info(self, interaction: discord.Interaction):
        """Show information about the matchmaking system"""
        # Get user's match status
        from utilities.utils2 import get_user_match_status
        
        match_status = await get_user_match_status(interaction.user)
        
        embed = discord.Embed(
            title="Matchmaking System Information",
            description="Here's how our matchmaking system works:",
            color=config.Colors.INFO
        )
        
        # Add user's match status at the top
        embed.add_field(
            name="Your Match Status",
            value=match_status["formatted_status"]+"\n",
            inline=False
        )

        embed.add_field(
            name="Finding Matches",
            value="- Use `/match find` to find your best match based on your roles.",
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
            value=f"- You can use the find match command once every {config.MATCH_COMMAND_COOLDOWN // 3600} hours.",
            inline=False
        )
        
        embed.add_field(
            name="Match Limits",
            value=f"""
- Regular users: {config.DEFAULT_MATCH_LIMIT} active matches
- Server Boosters: {config.BOOSTER_MATCH_LIMIT} active matches
- Premium Users: Unlimited active matches
            """,
            inline=False
        )

        embed.add_field(
            name="Unmatching",
            value="- Use `/match unmatch` if you want to end your current match and find someone new.",
            inline=False
        )

        embed.add_field(
            name="Opting Out",
            value="- Use `/match opt_out` if you want to stop receiving match requests.",
            inline=False
        )

        embed.add_field(
            name="Declined Matches",
            value=f"- If someone declines your match request, they won't appear in your matches for {config.DECLINED_MATCHES_EXCLUSION_DAYS} days.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot):
    await bot.add_cog(MatchmakingCog(bot))