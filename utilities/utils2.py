import discord
from discord import app_commands
import random
import logging
import config
import asyncio

logger = logging.getLogger("./errors/errors.log")

class MatchAcceptView(discord.ui.View):
    def __init__(self, match_id, target_user, requester_user, score, score_percentage):
        super().__init__(timeout=None)  # No timeout for persistent view
        self.match_id = match_id
        self.target_user = target_user
        self.requester_user = requester_user
        self.score = score
        self.score_percentage = score_percentage

    @discord.ui.button(label="Accept Match ✅", style=discord.ButtonStyle.success, custom_id="accept_match")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .matching_database import update_pending_match, add_match_history, update_match_status, get_pending_match

        # Handle persistent views after restart
        if self.target_user is None or self.requester_user is None:
            # Try to get match info from message ID
            message_id = interaction.message.id

            try:
                from .matching_database import get_pending_match_by_message_id
                match_data = get_pending_match_by_message_id(message_id)

                if match_data:
                    # Correctly unpack all 8 values from the pending_matches table
                    match_id, requester_id, target_id, score, message_id_db, created_at, expires_at, status = match_data

                    # Only the target can interact with accept/decline buttons
                    if interaction.user.id != target_id:
                        await interaction.response.send_message("This is not your match request to respond to!", ephemeral=True)
                        return

                    # If match is already handled, inform the user
                    if status != "pending":
                        await interaction.response.send_message(f"This match request has already been {status}.", ephemeral=True)
                        return

                    # Get user objects
                    try:
                        requester_user = await interaction.client.fetch_user(requester_id)
                        self.requester_user = requester_user
                        self.target_user = interaction.user
                        self.match_id = match_id
                        self.score = score
                        self.score_percentage = "{:.2f}".format((score / 100) * 100)  # Approximate percentage
                    except Exception as e:
                        logger.error(f"Error fetching users for persistent view: {e}")
                        await interaction.response.send_message("An error occurred processing this match request. Please try again later.", ephemeral=True)
                        return
                else:
                    await interaction.response.send_message("This match request is no longer valid.", ephemeral=True)
                    return
            except Exception as e:
                logger.error(f"Error retrieving match data for persistent view: {e}")
                await interaction.response.send_message("An error occurred. Please try again later.", ephemeral=True)
                return
        else:
            # Normal operation (not after restart)
            if interaction.user.id != self.target_user.id:
                await interaction.response.send_message("This is not your match request to respond to!", ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True)

        # Update pending match status
        update_pending_match(self.match_id, "accepted")

        # Add to match history
        match_id = add_match_history(
            self.requester_user.id, 
            self.target_user.id, 
            self.score, 
            "accepted"
        )

        # Add reciprocal entry for the other user
        add_match_history(
            self.target_user.id, 
            self.requester_user.id, 
            self.score, 
            "accepted"
        )

        # Update match status
        update_match_status(match_id, "accepted")

        # Send confirmation messages
        embed = discord.Embed(
            title="Match Accepted! ❤️",
            description=f"{self.target_user.mention} has accepted your match request!",
            color=config.Colors.SUCCESS
        )
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.add_field(
            name="Next Steps", 
            value="You can now send a direct message to start chatting!", 
            inline=False
        )
        embed.add_field(
            name="Match Score", 
            value=f"{self.score} ({self.score_percentage}% compatible)", 
            inline=False
        )
        embed.set_image(url=random.choice(config.LOVE_GIFS))

        try:
            await self.requester_user.send(embed=embed)
            await self.requester_user.send(
                f"Click here → **{interaction.user.mention}**\n\nIf it says 'unknown', send a friend request or search by username: `{interaction.user.name}`"
            )
        except discord.Forbidden:
            pass

        # Send confirmation to the target user
        await interaction.followup.send(
            content=f"You've accepted the match with {self.requester_user.mention}! You can now send them a direct message.\nIf it says 'unknown', send a friend request or search by username: `{self.requester_user.name}`",
            ephemeral=True
        )

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        # Update the original message
        embed = discord.Embed(
            title="Match Accepted! ❤️",
            description=f"You've accepted the match with {self.requester_user.mention}",
            color=config.Colors.SUCCESS
        )
        embed.set_thumbnail(url=self.requester_user.display_avatar.url)
        embed.set_image(url=random.choice(config.LOVE_GIFS))

        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Decline Match ❌", style=discord.ButtonStyle.danger, custom_id="decline_match")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .matching_database import update_pending_match, add_match_history, update_match_status, get_pending_match

        # Handle persistent views after restart
        if self.target_user is None or self.requester_user is None:
            # Try to get match info from message ID
            message_id = interaction.message.id

            try:
                from .matching_database import get_pending_match_by_message_id
                match_data = get_pending_match_by_message_id(message_id)

                if match_data:
                    # Correctly unpack all 8 values from the pending_matches table
                    match_id, requester_id, target_id, score, message_id_db, created_at, expires_at, status = match_data

                    # Only the target can interact with accept/decline buttons
                    if interaction.user.id != target_id:
                        await interaction.response.send_message("This is not your match request to respond to!", ephemeral=True)
                        return

                    # If match is already handled, inform the user
                    if status != "pending":
                        await interaction.response.send_message(f"This match request has already been {status}.", ephemeral=True)
                        return

                    # Get user objects
                    try:
                        requester_user = await interaction.client.fetch_user(requester_id)
                        self.requester_user = requester_user
                        self.target_user = interaction.user
                        self.match_id = match_id
                        self.score = score
                        self.score_percentage = "{:.2f}".format((score / 100) * 100)  # Approximate percentage
                    except Exception as e:
                        logger.error(f"Error fetching users for persistent view: {e}")
                        await interaction.response.send_message("An error occurred processing this match request. Please try again later.", ephemeral=True)
                        return
                else:
                    await interaction.response.send_message("This match request is no longer valid.", ephemeral=True)
                    return
            except Exception as e:
                logger.error(f"Error retrieving match data for persistent view: {e}")
                await interaction.response.send_message("An error occurred. Please try again later.", ephemeral=True)
                return
        else:
            # Normal operation (not after restart)
            if interaction.user.id != self.target_user.id:
                await interaction.response.send_message("This is not your match request to respond to!", ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True)

        # Update pending match status
        update_pending_match(self.match_id, "declined")

        # Add to match history
        match_id = add_match_history(
            self.requester_user.id, 
            self.target_user.id, 
            self.score, 
            "declined"
        )

        # Update match status
        update_match_status(match_id, "declined")

        # Notify the requester
        embed = discord.Embed(
            title="Match Declined",
            description=f"{self.target_user.mention} has declined your match request.",
            color=config.Colors.ERROR
        )
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.add_field(
            name="Don't worry!", 
            value="There are plenty of other potential matches out there!", 
            inline=False
        )

        try:
            await self.requester_user.send(embed=embed)
        except discord.Forbidden:
            pass

        # Confirm to the target
        await interaction.followup.send(
            content=f"You've declined the match with {self.requester_user.mention}.",
            ephemeral=True
        )

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        # Update the original message
        embed = discord.Embed(
            title="Match Declined",
            description=f"You've declined the match with {self.requester_user.mention}",
            color=config.Colors.ERROR
        )
        embed.set_thumbnail(url=self.requester_user.display_avatar.url)

        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Block User 🚫", style=discord.ButtonStyle.secondary, custom_id="block_user")
    async def block_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .matching_database import update_pending_match, block_user

        # Handle persistent views after restart
        if self.target_user is None or self.requester_user is None:
            # Try to get match info from message ID
            message_id = interaction.message.id

            try:
                from .matching_database import get_pending_match_by_message_id
                match_data = get_pending_match_by_message_id(message_id)

                if match_data:
                    match_id, requester_id, target_id, score, message_id_db, created_at, expires_at, status = match_data

                    # Only the target can interact with accept/decline buttons
                    if interaction.user.id != target_id:
                        await interaction.response.send_message("This is not your match request to respond to!", ephemeral=True)
                        return

                    # If match is already handled, inform the user
                    if status != "pending":
                        await interaction.response.send_message(f"This match request has already been {status}.", ephemeral=True)
                        return

                    # Get user objects
                    try:
                        requester_user = await interaction.client.fetch_user(requester_id)
                        self.requester_user = requester_user
                        self.target_user = interaction.user
                        self.match_id = match_id
                        self.score = score
                    except Exception as e:
                        logger.error(f"Error fetching users for persistent view: {e}")
                        await interaction.response.send_message("An error occurred processing this match request. Please try again later.", ephemeral=True)
                        return
                else:
                    await interaction.response.send_message("This match request is no longer valid.", ephemeral=True)
                    return
            except Exception as e:
                logger.error(f"Error retrieving match data for persistent view: {e}")
                await interaction.response.send_message("An error occurred. Please try again later.", ephemeral=True)
                return
        else:
            # Normal operation (not after restart)
            if interaction.user.id != self.target_user.id:
                await interaction.response.send_message("This is not your match request to respond to!", ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True)

        # Update pending match status
        update_pending_match(self.match_id, "blocked")

        # Add user to blocked list
        block_user(self.target_user.id, self.requester_user.id)

        # Confirm to the target
        await interaction.followup.send(
            content=f"You've blocked {self.requester_user.mention} from matching with you in the future.",
            ephemeral=True
        )
        # Notify the requester
        embed = discord.Embed(
            title="Match Declined",
            description=f"{self.target_user.mention} has declined your match request.",
            color=config.Colors.ERROR
        )
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.add_field(
            name="Don't worry!", 
            value="There are plenty of other potential matches out there!", 
            inline=False
        )

        try:
            await self.requester_user.send(embed=embed)
        except discord.Forbidden:
            pass

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        # Update the original message
        embed = discord.Embed(
            title="User Blocked",
            description=f"You've blocked {self.requester_user.mention} from matching with you",
            color=config.Colors.SECONDARY
        )
        embed.set_thumbnail(url=self.requester_user.display_avatar.url)

        await interaction.message.edit(embed=embed, view=self)

    async def on_timeout(self):
        from .matching_database import update_pending_match

        # Update pending match status
        update_pending_match(self.match_id, "expired")

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        # Update the original message if it still exists
        try:
            # Update the original message
            embed = discord.Embed(
                title="Match Request Expired",
                description=f"The match request from {self.requester_user.mention} has expired",
                color=config.Colors.SECONDARY
            )
            embed.set_thumbnail(url=self.requester_user.display_avatar.url)

            message = await self.target_user.fetch_message(self.message.id)
            await message.edit(embed=embed, view=self)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

class OptOutView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # No timeout for persistent view

    @discord.ui.button(label="Stop Finding Matches For Me", style=discord.ButtonStyle.danger, custom_id="opt_out_button")
    async def opt_out_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .matching_database import opt_out_user

        await interaction.response.defer(ephemeral=True)

        # Opt user out of matching
        opt_out_user(interaction.user.id, True)

        # Confirm to the user
        await interaction.followup.send(
            content="You have opted out of the matching system. Others won't be able to match with you anymore.",
            ephemeral=True
        )

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        # Update the original message
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary, custom_id="close_button")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        # Just close the message
        await interaction.message.delete()


class ProfileView(discord.ui.View):
    def __init__(self, matched_user):
        super().__init__(timeout=None)  # No timeout for persistent view
        self.matched_user = matched_user

    @discord.ui.button(label="Check Profile", style=discord.ButtonStyle.primary, custom_id="profile_button")
    async def profile_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Handle persistent views after restart
        if self.matched_user is None:
            # Try to get match info from database
            from .matching_database import has_active_match
            has_match, match_id, other_user_id = has_active_match(interaction.user.id)

            if not has_match:
                await interaction.response.send_message(
                    "You don't have an active match. This button is no longer valid.",
                    ephemeral=True
                )
                return

            try:
                # Get user object
                matched_user = await interaction.client.fetch_user(other_user_id)
                self.matched_user = matched_user
            except Exception as e:
                logger.error(f"Error fetching matched user for persistent view: {e}")
                await interaction.response.send_message(
                    "An error occurred. Please try again later.",
                    ephemeral=True
                )
                return

        await interaction.response.send_message(
            content=f"Click here to see their profile: {self.matched_user.mention}",
            ephemeral=True
        )

class UnmatchView(discord.ui.View):
    def __init__(self, match_id, matched_user):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.matched_user = matched_user

    @discord.ui.button(label="Unmatch", style=discord.ButtonStyle.danger, custom_id="unmatch_button")
    async def unmatch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .matching_database import unmatch_users, has_active_match
        # Handle persistent views after restart
        if self.matched_user is None:
            # Try to get match info from database
            has_match, match_id, other_user_id = has_active_match(interaction.user.id)

            if not has_match:
                await interaction.response.send_message(
                    "You don't have an active match. This button is no longer valid.",
                    ephemeral=True
                )
                return

            try:
                # Get user object
                matched_user = await interaction.client.fetch_user(other_user_id)
                self.matched_user = matched_user
                self.match_id = match_id
            except Exception as e:
                logger.error(f"Error fetching matched user for persistent view: {e}")
                await interaction.response.send_message(
                    "An error occurred processing this unmatch request. Please try again later.",
                    ephemeral=True
                )
                return

        try:
            success, user_id, matched_user_id = unmatch_users(self.match_id)

            if success:
                # Notify both users about the unmatch
                await interaction.response.send_message(
                    f"You have unmatched with {self.matched_user.mention}. You are now free to match with others!",
                    ephemeral=True
                )

                # Try to send a DM to the other user
                try:
                    embed = discord.Embed(
                        title="Match Update!",
                        description=f"{interaction.user.mention} has ended your match, it seems they don't know how amazing you're. lol,\nYou are now free to match with others.",
                        color=config.Colors.WARNING
                    )
                    await self.matched_user.send(embed=embed)
                except discord.Forbidden:
                    pass

                # Disable all buttons in the view
                for item in self.children:
                    item.disabled = True

                await interaction.message.edit(view=self)
            else:
                await interaction.response.send_message(
                    "There was an error unmatching. Please try again later.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error unmatching: {e}")
            await interaction.response.send_message(
                "Something went wrong. Please try again later.",
                ephemeral=True
            )

class UnmatchAndContinueView(discord.ui.View):
    def __init__(self, match_id, matched_user, partner_gender=None):
        super().__init__(timeout=None)  # No timeout for persistent view
        self.match_id = match_id
        self.matched_user = matched_user
        self.partner_gender = partner_gender

    @discord.ui.button(label="Unmatch and Find New Match", style=discord.ButtonStyle.primary, custom_id="unmatch_and_continue_button")
    async def unmatch_and_continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .matching_database import unmatch_users, has_active_match

        try:
            # Check if there's an active match first
            has_match, db_match_id, other_user_id = has_active_match(interaction.user.id)

            if not has_match:
                await interaction.response.send_message(
                    "You no longer have an active match. You can use /match find to find a new match.",
                    ephemeral=True
                )
                return

            # Unmatch using the match ID from the database (not from the view)
            success, user_id, matched_user_id = unmatch_users(db_match_id)

            if success:
                # Notify the user that they've been unmatched
                await interaction.response.send_message(
                    f"You have unmatched with {self.matched_user.mention}. Searching for a new match...",
                    ephemeral=True
                )

                # Try to send a DM to the other user
                try:
                    embed = discord.Embed(
                        title="Match Update!",
                        description=f"{interaction.user.mention} has ended your match, it seems they don't know how amazing you're. lol,\nYou are now free to match with others.",
                        color=config.Colors.WARNING
                    )
                    await self.matched_user.send(embed=embed)

                except discord.Forbidden:
                    # Can't send DM to the other user
                    pass

                try:
                    # Disable all buttons in the view
                    for item in self.children:
                        item.disabled = True

                    # Try to edit the message but don't error out if it fails
                    try:
                        await interaction.message.edit(view=self)
                    except discord.NotFound:
                        # Message might have been deleted or expired
                        pass
                except Exception as e:
                    logger.warning(f"Non-critical error disabling buttons: {e}")

                # Now trigger the find_match command with the same parameters
                if self.partner_gender:
                    # Use the ctx trick to call the command programmatically
                    cog = interaction.client.get_cog("MatchmakingCog")
                    if cog:
                        # Create a fake Choice object with the value
                        gender_choice = app_commands.Choice(name=self.partner_gender, value=self.partner_gender)
                        await cog.find_match(interaction, gender_choice)
                    else:
                        logger.error("Could not find MatchmakingCog when trying to continue match search")
            else:
                # Send the response via followup if the response was already sent
                try:
                    await interaction.response.send_message(
                        "There was an error unmatching. Please try again later.",
                        ephemeral=True
                    )
                except discord.InteractionResponded:
                    await interaction.followup.send(
                        "There was an error unmatching. Please try again later.",
                        ephemeral=True
                    )

        except Exception as e:
            logger.error(f"Error in unmatch_and_continue_button: {e}")
            # Send the response via followup if the response was already sent
            try:
                await interaction.response.send_message(
                    "Something went wrong. Please use the /match unmatch command instead.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    "Something went wrong. Please use the /match unmatch command instead.",
                    ephemeral=True
                )

    @discord.ui.button(label="Just Unmatch", style=discord.ButtonStyle.danger, custom_id="just_unmatch_button")
    async def just_unmatch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .matching_database import unmatch_users, has_active_match

        try:
            # Check if there's an active match first
            has_match, db_match_id, other_user_id = has_active_match(interaction.user.id)

            if not has_match:
                await interaction.response.send_message(
                    "You no longer have an active match.",
                    ephemeral=True
                )
                return

            # Unmatch using the match ID from the database (not from the view)
            success, user_id, matched_user_id = unmatch_users(db_match_id)

            if success:
                # Notify both users about the unmatch
                await interaction.response.send_message(
                    f"You have unmatched with {self.matched_user.mention}. You are now free to match with others!",
                    ephemeral=True
                )

                # Try to send a DM to the other user
                try:
                    embed = discord.Embed(
                        title="Match Update!",
                        description=f"{interaction.user.mention} has ended your match, it seems they don't know how amazing you're. lol,\nYou are now free to match with others.",
                        color=config.Colors.WARNING
                    )
                    await self.matched_user.send(embed=embed)
                except discord.Forbidden:
                    # Can't send DM to the other user
                    pass

                try:
                    # Disable all buttons in the view
                    for item in self.children:
                        item.disabled = True

                    # Try to edit the message but don't error out if it fails
                    try:
                        await interaction.message.edit(view=self)
                    except discord.NotFound:
                        # Message might have been deleted or expired
                        pass
                except Exception as e:
                    logger.warning(f"Non-critical error disabling buttons: {e}")
            else:
                # Send the response via followup if the response was already sent
                try:
                    await interaction.response.send_message(
                        "There was an error unmatching. Please try again later.",
                        ephemeral=True
                    )
                except discord.InteractionResponded:
                    await interaction.followup.send(
                        "There was an error unmatching. Please try again later.",
                        ephemeral=True
                    )

        except Exception as e:
            logger.error(f"Error unmatching: {e}")
            # Send the response via followup if the response was already sent
            try:
                await interaction.response.send_message(
                    "Something went wrong. Please use the /match unmatch command instead.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    "Something went wrong. Please use the /match unmatch command instead.",
                    ephemeral=True
                )

    @discord.ui.button(label="Keep Current Match", style=discord.ButtonStyle.secondary, custom_id="keep_match_button")
    async def keep_match_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message(
                f"You've chosen to stay matched with {self.matched_user.mention}.",
                ephemeral=True
            )

            try:
                # Disable all buttons in the view
                for item in self.children:
                    item.disabled = True

                # Try to edit the message but don't error out if it fails
                try:
                    await interaction.message.edit(view=self)
                except discord.NotFound:
                    # Message might have been deleted or expired
                    pass
            except Exception as e:
                logger.warning(f"Non-critical error disabling buttons: {e}")

        except Exception as e:
            logger.error(f"Error in keep_match_button: {e}")
            # Send the response via followup if the response was already sent
            try:
                await interaction.response.send_message(
                    f"You've chosen to stay matched with {self.matched_user.mention}.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    f"You've chosen to stay matched with {self.matched_user.mention}.",
                    ephemeral=True
                )


def format_user_info(user_data, user):
    """Format user information for display"""
    if not user_data:
        return "No profile data available"

    parts = []

    # Basic info
    if user_data.get("gender"):
        parts.append(f"**Gender:** {user_data['gender']}")

    if user_data.get("age"):
        parts.append(f"**Age:** {user_data['age']} years old")

    if user_data.get("height"):
        height = user_data["height"]
        if len(str(height)) >= 2:
            # Format height as feet and inches (e.g., "5'10")
            parts.append(f"**Height:** {str(height)[0]}'{str(height)[1:]}")
        else:
            parts.append(f"**Height:** {height}")

    if user_data.get("region"):
        parts.append(f"**Region:** {user_data['region']}")

    if user_data.get("personality") and len(user_data["personality"]) > 0:
        parts.append(f"**Personality:** {', '.join(user_data['personality'])}")

    if user_data.get("relationship_status"):
        parts.append(f"**Relationship Status:** {user_data['relationship_status']}")

    if user_data.get("dms_status"):
        parts.append(f"**DMs Status:** {user_data['dms_status']}")

    # Preferences
    if user_data.get("height_preference"):
        parts.append(f"**Height Preference:** {user_data['height_preference']}")

    if user_data.get("age_preference"):
        parts.append(f"**Age Preference:** {user_data['age_preference']}")

    if user_data.get("distance_preference"):
        parts.append(f"**Distance Preference:** {user_data['distance_preference']}")

    if user_data.get("personality_preference") and len(user_data["personality_preference"]) > 0:
        parts.append(f"**Personality Preference:** {', '.join(user_data['personality_preference'])}")

    if user_data.get("hobbies") and len(user_data["hobbies"]) > 0:
        parts.append(f"**Hobbies:** {', '.join(user_data['hobbies'])}")

    if user_data.get("sexuality"):
        parts.append(f"**Sexuality:** {user_data['sexuality']}")

    return "\n".join(parts)

async def get_user_match_status(member):
    """
    Get match information for a user, including current match count,
    match limit, and formatted status information.
    
    Parameters:
    - member: discord.Member object
    
    Returns:
    - Dictionary with match information:
        - active_match_count: Number of active matches
        - match_limit: User's match limit (0 means unlimited)
        - is_unlimited: True if user has unlimited matches
        - has_reached_limit: True if user has reached their match limit
        - matches_remaining: Number of matches remaining (None if unlimited)
        - formatted_status: Formatted message about match status
    """
    from .matching_database import get_all_active_matches, get_match_limit
    
    # Get current active matches
    active_matches = get_all_active_matches(member.id)
    
    # Count unique users in the match list
    unique_match_users = set()
    for match in active_matches:
        unique_match_users.add(match['other_user_id'])
    
    active_match_count = len(unique_match_users)
    
    # Get user's match limit
    match_limit = get_match_limit(member)
    is_unlimited = (match_limit == 0)
    has_reached_limit = (match_limit > 0 and active_match_count >= match_limit)
    
    # Calculate matches remaining
    matches_remaining = None
    if not is_unlimited:
        matches_remaining = match_limit - active_match_count
    
    # Format status message
    formatted_status = ""
    if is_unlimited:
        formatted_status = f"You currently have {active_match_count} active match{'es' if active_match_count != 1 else ''} with unlimited capacity 💎"
    elif active_match_count == 0:
        formatted_status = f"You don't have any active matches (Limit: {match_limit})"
    elif has_reached_limit:
        formatted_status = f"You've reached your limit of {match_limit} active matches."
    else:
        formatted_status = f"You have {active_match_count}/{match_limit} active matches (space for {matches_remaining} more)."
    
    return {
        "active_match_count": active_match_count,
        "match_limit": match_limit,
        "is_unlimited": is_unlimited,
        "has_reached_limit": has_reached_limit,
        "matches_remaining": matches_remaining,
        "formatted_status": formatted_status
    }

def create_match_embed(requester, target, score, max_score, user_data):
    """Create an embed for a match"""
    # Format score percentage to always show 2 decimal places
    score_percentage = "{:.2f}".format((score / max_score) * 100)

    embed = discord.Embed(
        title="✨ New Match Found! ✨",
        description=f"We found a potential match for you!",
        color=config.Colors.LOVE
    )
    embed.add_field(
        name="Match Score", 
        value=f"{score} points ({score_percentage}% compatible)", 
        inline=False
    )

    # Add user information
    embed.add_field(
        name=f"About Them", 
        value=format_user_info(user_data, target), 
        inline=False
    )
    embed.add_field(
        name="Why can't I see their Discord name?",
        value="To protect privacy, we don’t share their username until they accept your match request.",
        inline=False
    )
    embed.set_footer(text="Match requests expire after 24 hours")
    embed.set_image(url=random.choice(config.LOVE_GIFS))

    return embed

async def send_match_request(requester, target, score, max_score, user_data):
    """Send a match request to the target user"""
    from .matching_database import add_pending_match

    # Format score percentage to always show 2 decimal places
    score_percentage = "{:.2f}".format((score / max_score) * 100)

    # Create match embed for target
    embed = discord.Embed(
        title="💖 New Match Request! 💖",
        description=f"{requester.mention} would like to match with you!",
        color=config.Colors.LOVE
    )

    embed.set_thumbnail(url=requester.display_avatar.url)
    embed.add_field(
        name="Match Score", 
        value=f"{score} points ({score_percentage}% compatible)", 
        inline=False
    )

    # Add requester information
    embed.add_field(
        name=f"About {requester.display_name}", 
        value=format_user_info(user_data, requester), 
        inline=False
    )

    embed.add_field(
        name="What would you like to do?", 
        value="Use the buttons below to accept or decline this match request.", 
        inline=False
    )

    embed.set_footer(text="This request will expire in 24 hours")
    embed.set_image(url=random.choice(config.LOVE_GIFS))

    # Create view with buttons
    view = MatchAcceptView(
        match_id=None,  # Will be updated after adding to .matching_database
        target_user=target,
        requester_user=requester,
        score=score,
        score_percentage=score_percentage
    )

    try:
        # Send DM to target
        message = await target.send(embed=embed, view=view)

        # Add pending match to .matching_database
        match_id = add_pending_match(
            requester_id=requester.id,
            target_id=target.id,
            score=score,
            message_id=message.id
        )

        # Update view with match ID
        if match_id is not None:
            view.match_id = match_id

        return True, match_id
    except discord.Forbidden:
        logger.warning(f"Could not send DM to target user {target.id}")
        return False, None
    except Exception as e:
        logger.error(f"Error sending match request: {e}")
        return False, None

def check_user_roles(member, role_parser):
    """Check if the user has required roles"""
    # First check for required roles
    has_required, missing_msg = role_parser.check_required_roles(member)
    if not has_required:
        return False, missing_msg

    # Then check user data
    user_data = role_parser.extract_user_data(member)

    # Check for exclusion roles
    if user_data and user_data.get("exclusion_roles") and len(user_data["exclusion_roles"]) > 0:
        return False, "You have roles that exclude you from matching (such as 'taken' or 'not looking')"

    # Check if user has DMs closed
    if user_data and user_data.get("dms_status") == "dms closed":
        return False, "You have DMs closed. Please change your DMs status role to use the matching system."

    return True, None

async def cleanup_task(bot):
    """Task to clean up expired matches"""
    from .matching_database import cleanup_expired_matches

    while True:
        try:
            # Clean up expired matches
            cleanup_expired_matches()

            # Sleep for an hour
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60)  # Sleep for a minute on error