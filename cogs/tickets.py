import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
import logging
import io
from datetime import datetime
import chat_exporter
from typing import Dict, List, Optional, Union
import re
from errors.error_logger import error_send
from utilities.get_template import get_message_from_template, get_message_from_dict
from utilities.colors import *

# Configure logging
logger = logging.getLogger('dating_ticket_bot.tickets')

# Handler classes for ticket buttons
class TicketButtonsWithHandlers:
    def __init__(self, bot):
        self.bot = bot

    async def handle_close(self, interaction: discord.Interaction, status: str):
        # Load config
        with open('config.json', 'r') as f:
            config = json.load(f)

        # Check if user has permission to close the ticket
        if not any(role.id in [int(r) for r in config["guilds"][str(interaction.guild.id)]["staff_roles"]] 
                   for role in interaction.user.roles):
            await interaction.followup.send(
                "❌ You don't have permission to close this ticket.", 
                ephemeral=True
            )
            return

        # Get ticket information
        ticket_creator = None
        ticket_type = None

        # Extract ticket creator from channel permissions
        for member, perms in interaction.channel.overwrites.items():
            if isinstance(member, discord.Member) and perms.read_messages:
                # Skip staff and bots
                if not any(role.id in [int(r) for r in config["guilds"][str(interaction.guild.id)]["staff_roles"]] 
                       for role in member.roles) and not member.bot:
                    ticket_creator = member
                    break

        # Extract ticket type from channel name
        channel_name_parts = interaction.channel.name.split('-')
        if len(channel_name_parts) >= 2:
            ticket_type = channel_name_parts[0]

        # Send closing message
        status_emoji = "✅" if status == "resolved" else "🔒"
        status_text = "resolved" if status == "resolved" else "closed"

        await interaction.channel.send(
            f"{status_emoji} This ticket has been {status_text} by {interaction.user.mention}. "
            f"The channel will be deleted soon"
        )

        # Send a DM to the ticket creator
        if ticket_creator:
            try:
                # Load the ticket closure template file directly
                with open('templates/ticket_closure.json', 'r', encoding='utf-8') as f:
                    all_closure_templates = json.load(f)
                
                # Get the correct closure template based on status
                if status in all_closure_templates:
                    closure_template = all_closure_templates[status]
                    
                    data = get_message_from_dict(closure_template, {"server_name":interaction.guild.name})
                    if data.get("embeds") or data.get("content"):
                        await ticket_creator.send(content=data.get("content"), embeds=data.get("embeds"))

            except Exception as e:
                logger.error(f"Error sending ticket closure DM: {e}")
                # Continue with ticket closure even if DM fails
  

        # Generate transcript
        try:
            transcript = await chat_exporter.export(
                channel=interaction.channel,
                limit=None,
                tz_info="UTC",
                guild=interaction.guild,
                bot=self.bot
            )

            if transcript:
                transcript_file = discord.File(
                    io.BytesIO(transcript.encode()),
                    filename=f"transcript-{interaction.channel.name}.html"
                )

                # Find the log channel
                log_channel_id = config["guilds"][str(interaction.guild.id)]["ticket_log_channel_id"]
                if log_channel_id:
                    log_channel = interaction.guild.get_channel(int(log_channel_id))
                    if log_channel:
                        # Send the log with transcript
                        ticket_message = get_message_from_template("ticket_log", {
                            "ticket_channel": interaction.channel.name,
                            "closed_by": interaction.user.name,
                            "closed_by_id": interaction.user.id,
                            "status": status_text,
                            "timestamp": int(datetime.now().timestamp())
                        })

                        await log_channel.send(
                            content=ticket_message["content"],
                            embeds=ticket_message["embeds"],
                            file=transcript_file
                        )

        except Exception as e:
            await error_send()
            await interaction.followup.send(
                "❌ There was an error generating the transcript.", 
                ephemeral=True
            )

        # Wait and delete the channel
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket {status_text} by {interaction.user.name}")
        except Exception as e:
            await error_send()
            await interaction.followup.send(
                "❌ There was an error deleting the channel. Please delete it manually.", 
                ephemeral=True
            )

# Handler classes for application buttons
class ApplicationButtonsWithHandlers:
    def __init__(self, bot):
        self.bot = bot

    async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has permission to accept applications
        with open('config.json', 'r') as f:
            config = json.load(f)

        guild_id = str(interaction.guild.id)
        staff_role_ids = config["guilds"][guild_id]["staff_roles"]

        if not any(role.id in [int(r) for r in staff_role_ids] for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Only staff members can accept applications.", 
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)

        # Find the applicant (first member with read access who isn't staff or bot)
        applicant = None
        for member, perms in interaction.channel.overwrites.items():
            if isinstance(member, discord.Member) and perms.read_messages:
                if not any(role.id in [int(r) for r in staff_role_ids] for role in member.roles) and not member.bot:
                    applicant = member
                    break

        if not applicant:
            await interaction.followup.send("❌ Could not find the applicant.")
            return

        # Check if trial staff role is configured
        trial_role = None
        if "trial_staff_role_id" in config["guilds"][guild_id]:
            trial_role_id = config["guilds"][guild_id]["trial_staff_role_id"]
            trial_role = interaction.guild.get_role(int(trial_role_id))

        if not trial_role:
            await interaction.followup.send("❌ Trial staff role not configured or no longer exists.")
            return

        # Add trial role to applicant
        try:
            await applicant.add_roles(trial_role, reason="Staff application accepted")

            # Send acceptance DM
            try:
                # Load the application results template file directly
                with open('templates/application_results.json', 'r', encoding='utf-8') as f:
                    all_results = json.load(f)
                
                # Get the accepted result template
                if "accepted" in all_results:
                    accepted_template = all_results["accepted"]
                    
                    # Format variables in the template
                    # For content
                    content = accepted_template.get("content", "")
                    if content:
                        content = content.format(
                            server_name=interaction.guild.name,
                            timestamp=int(datetime.now().timestamp())
                        )
                    
                    # For embeds
                    embeds = []
                    if "embeds" in accepted_template and accepted_template["embeds"]:
                        for embed_data in accepted_template["embeds"]:
                            # Create the embed
                            embed = discord.Embed(
                                title=embed_data.get("title", "").format(
                                    server_name=interaction.guild.name,
                                    timestamp=int(datetime.now().timestamp())
                                ),
                                description=embed_data.get("description", "").format(
                                    server_name=interaction.guild.name,
                                    timestamp=int(datetime.now().timestamp())
                                ),
                                color=int(embed_data.get("color", "c40000").lstrip("#"), 16)
                            )
                            
                            # Add footer if present
                            if "footer" in embed_data and embed_data["footer"]:
                                embed.set_footer(text=embed_data["footer"].get("text", ""))
                            
                            # Add timestamp if present
                            if "timestamp" in embed_data and embed_data["timestamp"]:
                                if embed_data["timestamp"] == "{timestamp}":
                                    embed.timestamp = datetime.fromtimestamp(int(datetime.now().timestamp()))
                            
                            embeds.append(embed)
                    
                    # Send the DM
                    if embeds or content:
                        await applicant.send(content=content, embeds=embeds)
                        logger.info(f"Sent acceptance DM to {applicant.name}")
            except Exception as e:
                logger.error(f"Error sending acceptance DM: {e}")
                await error_send()

            # Close the ticket
            await interaction.followup.send(
                f"✅ Application for {applicant.mention} has been accepted! They have been given the {trial_role.mention} role. The ticket will close soon"
            )

            await asyncio.sleep(5)
            await interaction.channel.delete(reason=f"Staff application for {applicant.name} accepted by {interaction.user.name}")

        except Exception as e:
            await error_send()
            await interaction.followup.send(f"❌ Error: {str(e)}")

    async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has permission to reject applications
        with open('config.json', 'r') as f:
            config = json.load(f)

        guild_id = str(interaction.guild.id)
        staff_role_ids = config["guilds"][guild_id]["staff_roles"]

        if not any(role.id in [int(r) for r in staff_role_ids] for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Only staff members can reject applications.", 
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)

        # Find the applicant (first member with read access who isn't staff or bot)
        applicant = None
        for member, perms in interaction.channel.overwrites.items():
            if isinstance(member, discord.Member) and perms.read_messages:
                if not any(role.id in [int(r) for r in staff_role_ids] for role in member.roles) and not member.bot:
                    applicant = member
                    break

        if not applicant:
            await interaction.followup.send("❌ Could not find the applicant.")
            return

        # Send rejection DM
        try:
            # Load the application results template file directly
            with open('templates/application_results.json', 'r', encoding='utf-8') as f:
                all_results = json.load(f)
            
            # Get the rejected result template
            if "rejected" in all_results:
                rejected_template = all_results["rejected"]
                
                # Format variables in the template
                # For content
                content = rejected_template.get("content", "")
                if content:
                    content = content.format(
                        server_name=interaction.guild.name,
                        timestamp=int(datetime.now().timestamp())
                    )
                
                # For embeds
                embeds = []
                if "embeds" in rejected_template and rejected_template["embeds"]:
                    for embed_data in rejected_template["embeds"]:
                        # Create the embed
                        embed = discord.Embed(
                            title=embed_data.get("title", "").format(
                                server_name=interaction.guild.name,
                                timestamp=int(datetime.now().timestamp())
                            ),
                            description=embed_data.get("description", "").format(
                                server_name=interaction.guild.name,
                                timestamp=int(datetime.now().timestamp())
                            ),
                            color=int(embed_data.get("color", "c40000").lstrip("#"), 16)
                        )
                        
                        # Add footer if present
                        if "footer" in embed_data and embed_data["footer"]:
                            embed.set_footer(text=embed_data["footer"].get("text", ""))
                        
                        # Add timestamp if present
                        if "timestamp" in embed_data and embed_data["timestamp"]:
                            if embed_data["timestamp"] == "{timestamp}":
                                embed.timestamp = datetime.fromtimestamp(int(datetime.now().timestamp()))
                        
                        embeds.append(embed)
                
                # Send the DM
                if embeds or content:
                    await applicant.send(content=content, embeds=embeds)
                    logger.info(f"Sent rejection DM to {applicant.name}")
        except Exception as e:
            logger.error(f"Error sending rejection DM: {e}")
            # Continue with ticket closure even if DM fails

        # Close the ticket
        await interaction.followup.send(
            f"❌ Application for {applicant.mention} has been rejected. The ticket will close in soon"
        )

        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Staff application for {applicant.name} rejected by {interaction.user.name}")

class TicketView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.select(
        placeholder="Select ticket reason",
        custom_id="ticket_select",
        options=[
            discord.SelectOption(
                label="Support", 
                description="Get help from our team", 
                emoji="💕",
                value="support"
            ),
            discord.SelectOption(
                label="Report a Member", 
                description="Report inappropriate behavior", 
                emoji="🚫",
                value="report"
            ),
            discord.SelectOption(
                label="Staff Application", 
                description="Apply to join our staff team", 
                emoji="📝",
                value="application"
            ),
            discord.SelectOption(
                label="Verification", 
                description="Verify your age and identity", 
                emoji="✅",
                value="verification"
            )
        ]
    )
    async def ticket_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await self.create_ticket(interaction, select.values[0])

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        # Load config
        with open('config.json', 'r') as f:
            config = json.load(f)

        guild_id = str(interaction.guild.id)

        # Check if the guild has been set up
        if guild_id not in config["guilds"] or not config["guilds"][guild_id]["ticket_category_id"]:
            await interaction.response.send_message(
                "❌ Ticket system hasn't been set up for this server yet. Please ask an admin to set it up.", 
                ephemeral=True
            )
            return

        # Get ticket values
        guild_config = config["guilds"][guild_id]
        category_id = guild_config["ticket_category_id"]
        staff_role_ids = guild_config["staff_roles"]

        # Get category
        category = interaction.guild.get_channel(int(category_id))
        if not category:
            await interaction.response.send_message(
                "❌ The ticket category no longer exists. Please ask an admin to reconfigure the bot.", 
                ephemeral=True
            )
            return

        # Get ticket reason display name
        ticket_reason_map = {
            "support": "Support Request",
            "report": "Member Report",
            "application": "Staff Application",
            "verification": "Verification Request"
        }
        ticket_reason = ticket_reason_map.get(ticket_type, "Support")
        emoji = {
            "support": "🚨",
            "report": "⚠️",
            "application": "📝",
            "verification": "✔️"
        }
        # Create ticket channel name
        user_name = re.sub(r'[^\w\s]', '', interaction.user.name.lower())
        user_name = re.sub(r'\s+', '-', user_name)
        channel_name = f"{emoji.get(ticket_type, '⚠️')}│{user_name}"

        # Check if user already has an open ticket of this type
        existing_tickets = [c for c in category.channels if c.name.startswith(f"{ticket_type}-{user_name}")]
        if existing_tickets:
            await interaction.response.send_message(
                f"❌ You already have an open {ticket_reason.lower()} ticket. Please use that one instead.", 
                ephemeral=True
            )
            return

        # Let the user know we're creating their ticket
        await interaction.response.send_message(
            f"💖 Creating your {ticket_reason.lower()} ticket...", 
            ephemeral=True
        )

        # Set up permissions
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        # Add staff role permissions
        for role_id in staff_role_ids:
            role = interaction.guild.get_role(int(role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True)

        # Create the ticket channel
        try:
            ticket_channel = await category.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                reason=f"Ticket created by {interaction.user.name} for {ticket_reason}"
            )

            # Send the ticket welcome message
            ticket_message = get_message_from_template("ticket_channel", {
                "user": interaction.user.mention,
                "user_name": interaction.user.name,
                "reason": ticket_reason,
                "ticket_type": ticket_type,
                "timestamp": int(datetime.now().timestamp())
            })

            # Create button callbacks for ticket management
            class TicketButtons(discord.ui.View):
                def __init__(self, bot):
                    super().__init__(timeout=None)
                    self.bot = bot

                @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket")
                async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.defer(ephemeral=True)
                    await self.handle_close(interaction, "closed")

                @discord.ui.button(label="Resolved", emoji="✅", style=discord.ButtonStyle.success, custom_id="resolve_ticket")
                async def resolve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.defer(ephemeral=True)
                    await self.handle_close(interaction, "resolved")

                @discord.ui.button(label="Add Member", emoji="👤", style=discord.ButtonStyle.primary, custom_id="add_member")
                async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
                    # Check if user has permission (is a staff member)
                    with open('config.json', 'r') as f:
                        config = json.load(f)

                    guild_id = str(interaction.guild.id)
                    staff_role_ids = config["guilds"][guild_id]["staff_roles"]

                    if not any(role.id in [int(r) for r in staff_role_ids] for role in interaction.user.roles):
                        await interaction.response.send_message(
                            "❌ Only staff members can add users to tickets.", 
                            ephemeral=True
                        )
                        return

                    # Create a modal to add a member
                    class AddMemberModal(discord.ui.Modal, title="Add Member to Ticket"):
                        member_id = discord.ui.TextInput(
                            label="Member ID or @mention",
                            placeholder="Enter member ID or @mention (e.g., 123456789012345678 or @username)",
                            min_length=5,
                            max_length=50,
                            required=True
                        )

                        async def on_submit(self, interaction: discord.Interaction):
                            # Parse the member ID
                            member_input = self.member_id.value.strip()

                            # Extract ID from mention if needed
                            if member_input.startswith('<@') and member_input.endswith('>'):
                                member_input = member_input[2:-1]
                                if member_input.startswith('!'):
                                    member_input = member_input[1:]

                            try:
                                member_id = int(member_input)
                                member = interaction.guild.get_member(member_id)

                                if not member:
                                    await interaction.response.send_message(
                                        "❌ Could not find that member. Make sure they're in this server.", 
                                        ephemeral=True
                                    )
                                    return

                                # Check if member already has access to the ticket
                                existing_perms = interaction.channel.permissions_for(member)
                                if existing_perms.read_messages:
                                    await interaction.response.send_message(
                                        f"❌ {member.mention} already has access to this ticket.", 
                                        ephemeral=True
                                    )
                                    return

                                # Add member to the ticket
                                await interaction.channel.set_permissions(
                                    member,
                                    read_messages=True,
                                    send_messages=True,
                                    attach_files=True,
                                    embed_links=True
                                )

                                await interaction.response.send_message(
                                    f"💖 {member.mention} has been added to the ticket by {interaction.user.mention}",
                                )

                            except ValueError:
                                await interaction.response.send_message(
                                    "❌ Invalid member ID format. Please use a valid ID or mention.", 
                                    ephemeral=True
                                )

                    await interaction.response.send_modal(AddMemberModal())

                async def handle_close(self, interaction: discord.Interaction, status: str):
                    ticket_button_view = TicketButtonsWithHandlers(self.bot)
                    await ticket_button_view.handle_close(interaction, status)
                    
            # Send the ticket message with buttons
            ticket_buttons = TicketButtons(self.bot)
            await ticket_channel.send(
                content=ticket_message["content"],
                embeds=ticket_message["embeds"],
                view=ticket_buttons
            )

            # Ping the user and staff
            ping_message = f"{interaction.user.mention}"
            if ticket_type == "report" or ticket_type == "support":
                for role_id in staff_role_ids:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        ping_message += f" {role.mention}"

            await ticket_channel.send(ping_message)

            # Add type-specific content
            if ticket_type == "verification":
                # Send verification instructions
                verification_message = get_message_from_template("verification_instructions", {
                    "server_name": interaction.guild.name,
                    "timestamp": int(datetime.now().timestamp())
                })

                await ticket_channel.send(
                    content=verification_message["content"],
                    embeds=verification_message["embeds"]
                )

            elif ticket_type == "application":
                # Send staff application questions
                application_message = get_message_from_template("staff_application", {
                    "server_name": interaction.guild.name,
                    "timestamp": int(datetime.now().timestamp())
                })

                # Create application buttons
                class ApplicationButtons(discord.ui.View):
                    def __init__(self, bot):
                        super().__init__(timeout=None)
                        self.bot = bot

                    @discord.ui.button(label="Accept Application", emoji="✅", style=discord.ButtonStyle.success, custom_id="accept_application")
                    async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
                        # Check if user has permission to accept applications
                        with open('config.json', 'r') as f:
                            config = json.load(f)

                        guild_id = str(interaction.guild.id)
                        staff_role_ids = config["guilds"][guild_id]["staff_roles"]

                        if not any(role.id in [int(r) for r in staff_role_ids] for role in interaction.user.roles):
                            await interaction.response.send_message(
                                "❌ Only staff members can accept applications.", 
                                ephemeral=True
                            )
                            return

                        await interaction.response.defer(ephemeral=False)

                        # Find the applicant (first member with read access who isn't staff or bot)
                        applicant = None
                        for member, perms in interaction.channel.overwrites.items():
                            if isinstance(member, discord.Member) and perms.read_messages:
                                if not any(role.id in [int(r) for r in staff_role_ids] for role in member.roles) and not member.bot:
                                    applicant = member
                                    break

                        if not applicant:
                            await interaction.followup.send("❌ Could not find the applicant.")
                            return

                        # Check if trial staff role is configured
                        trial_role = None
                        if "trial_staff_role_id" in config["guilds"][guild_id]:
                            trial_role_id = config["guilds"][guild_id]["trial_staff_role_id"]
                            trial_role = interaction.guild.get_role(int(trial_role_id))

                        if not trial_role:
                            await interaction.followup.send("❌ Trial staff role not configured or no longer exists.")
                            return

                        # Add trial role to applicant
                        try:
                            await applicant.add_roles(trial_role, reason="Staff application accepted")

                            # Send acceptance DM
                            try:
                                acceptance_results = get_message_from_template("application_results", {
                                    "server_name": interaction.guild.name,
                                    "timestamp": int(datetime.now().timestamp())
                                })

                                if isinstance(acceptance_results, dict) and "accepted" in acceptance_results:
                                    accepted_dm = acceptance_results["accepted"]

                                    # Only include what's available in the message
                                    kwargs = {}
                                    if "content" in accepted_dm:
                                        kwargs["content"] = accepted_dm["content"]
                                    if "embeds" in accepted_dm:
                                        kwargs["embeds"] = accepted_dm["embeds"]

                                    # Send the DM with only the available components
                                    if kwargs:
                                        await applicant.send(**kwargs)
                            except Exception as e:
                                await error_send()

                            # Close the ticket
                            await interaction.followup.send(
                                f"✅ Application for {applicant.mention} has been accepted! They have been given the {trial_role.mention} role. The ticket will close soon"
                            )

                            await asyncio.sleep(5)
                            await interaction.channel.delete(reason=f"Staff application for {applicant.name} accepted by {interaction.user.name}")

                        except Exception as e:
                            await error_send()
                            await interaction.followup.send(f"❌ Error: {str(e)}")

                    @discord.ui.button(label="Reject Application", emoji="❌", style=discord.ButtonStyle.danger, custom_id="reject_application")
                    async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
                        # Check if user has permission to reject applications
                        with open('config.json', 'r') as f:
                            config = json.load(f)

                        guild_id = str(interaction.guild.id)
                        staff_role_ids = config["guilds"][guild_id]["staff_roles"]

                        if not any(role.id in [int(r) for r in staff_role_ids] for role in interaction.user.roles):
                            await interaction.response.send_message(
                                "❌ Only staff members can reject applications.", 
                                ephemeral=True
                            )
                            return

                        await interaction.response.defer(ephemeral=False)

                        # Find the applicant (first member with read access who isn't staff or bot)
                        applicant = None
                        for member, perms in interaction.channel.overwrites.items():
                            if isinstance(member, discord.Member) and perms.read_messages:
                                if not any(role.id in [int(r) for r in staff_role_ids] for role in member.roles) and not member.bot:
                                    applicant = member
                                    break

                        if not applicant:
                            await interaction.followup.send("❌ Could not find the applicant.")
                            return

                        # Send rejection DM
                        try:
                            rejection_results = get_message_from_template("application_results", {
                                "server_name": interaction.guild.name,
                                "timestamp": int(datetime.now().timestamp())
                            })

                            if isinstance(rejection_results, dict) and "rejected" in rejection_results:
                                rejected_dm = rejection_results["rejected"]

                                # Only include what's available in the message
                                kwargs = {}
                                if "content" in rejected_dm:
                                    kwargs["content"] = rejected_dm["content"]
                                if "embeds" in rejected_dm:
                                    kwargs["embeds"] = rejected_dm["embeds"]

                                # Send the DM with only the available components
                                if kwargs:
                                    await applicant.send(**kwargs)
                        except Exception as e:
                            await error_send()

                        # Close the ticket
                        await interaction.followup.send(
                            f"❌ Application for {applicant.mention} has been rejected. The ticket will  close soon"
                        )

                        await asyncio.sleep(5)
                        await interaction.channel.delete(reason=f"Staff application for {applicant.name} rejected by {interaction.user.name}")

                app_view = ApplicationButtons(self.bot)
                await ticket_channel.send(
                    content=application_message["content"],
                    embeds=application_message["embeds"],
                    view=app_view
                )

            # Send a followup message to the user
            await interaction.followup.send(
                f"✅ Your ticket has been created! Please check {ticket_channel.mention}", 
                ephemeral=True
            )

            # Send a DM notification based on ticket type
            try:
                # Load the ticket DM template file directly
                with open('templates/ticket_dm.json', 'r', encoding='utf-8') as f:
                    all_dm_templates = json.load(f)
                
                # Check if this ticket type has a DM template
                if ticket_type in all_dm_templates:
                    dm_template = all_dm_templates[ticket_type]
                    
                    # Format variables in the template
                    # For content
                    content = dm_template.get("content", "")
                    if content:
                        content = content.format(
                            server_name=interaction.guild.name,
                            ticket_channel=ticket_channel.mention,
                            timestamp=int(datetime.now().timestamp())
                        )
                    
                    # For embeds
                    embeds = []
                    if "embeds" in dm_template and dm_template["embeds"]:
                        for embed_data in dm_template["embeds"]:
                            # Create the embed
                            embed = discord.Embed(
                                title=embed_data.get("title", "").format(
                                    server_name=interaction.guild.name,
                                    ticket_channel=ticket_channel.mention,
                                    timestamp=int(datetime.now().timestamp())
                                ),
                                description=embed_data.get("description", "").format(
                                    server_name=interaction.guild.name,
                                    ticket_channel=ticket_channel.mention,
                                    timestamp=int(datetime.now().timestamp())
                                ),
                                color=int(embed_data.get("color", "c40000").lstrip("#"), 16)
                            )
                            
                            # Add footer if present
                            if "footer" in embed_data and embed_data["footer"]:
                                embed.set_footer(text=embed_data["footer"].get("text", ""))
                            
                            # Add timestamp if present
                            if "timestamp" in embed_data and embed_data["timestamp"]:
                                if embed_data["timestamp"] == "{timestamp}":
                                    embed.timestamp = datetime.fromtimestamp(int(datetime.now().timestamp()))
                            
                            embeds.append(embed)
                    
                    # Send the DM
                    if embeds or content:
                        await interaction.user.send(content=content, embeds=embeds)
                        logger.info(f"Sent DM notification for {ticket_type} ticket to {interaction.user.name}")
                
            except Exception as e:
                logger.error(f"Error sending DM notification: {e}")
                # Don't notify the user if the DM fails - they already have the ticket channel

        except Exception as e:
            await error_send()
            await interaction.followup.send(
                "❌ There was an error creating your ticket. Please try again later or contact an admin.", 
                ephemeral=True
            )

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Register the persistent views on bot startup
        bot.add_view(TicketView(bot))  # Register ticket creation view
        
        # Register ticket management buttons
        class TicketButtons(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket")
            async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                ticket_handler = TicketButtonsWithHandlers(bot)
                await ticket_handler.handle_close(interaction, "closed")

        # Add the ticket buttons view
        bot.add_view(TicketButtons())

        # Register the TicketButtons view to handle button interactions in existing tickets
        class TicketButtons(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)

            @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket")
            async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                # Get the actual ticket view instance
                ticket_button_view = TicketButtonsWithHandlers(bot)
                await ticket_button_view.handle_close(interaction, "close")

            @discord.ui.button(label="Resolved", emoji="✅", style=discord.ButtonStyle.success, custom_id="resolve_ticket")
            async def resolve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                # Get the actual ticket view instance
                ticket_button_view = TicketButtonsWithHandlers(bot)
                await ticket_button_view.handle_close(interaction, "resolved")

            @discord.ui.button(label="Add Member", emoji="👤", style=discord.ButtonStyle.primary, custom_id="add_member")
            async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Check if user has permission (is a staff member)
                with open('config.json', 'r') as f:
                    config = json.load(f)

                guild_id = str(interaction.guild.id)
                staff_role_ids = config["guilds"][guild_id]["staff_roles"]

                if not any(role.id in [int(r) for r in staff_role_ids] for role in interaction.user.roles):
                    await interaction.response.send_message(
                        "❌ Only staff members can add users to tickets.", 
                        ephemeral=True
                    )
                    return

                # Create a modal to add a member
                class AddMemberModal(discord.ui.Modal, title="Add Member to Ticket"):
                    member_id = discord.ui.TextInput(
                        label="Member ID or @mention",
                        placeholder="Enter member ID or @mention (e.g., 123456789012345678 or @username)",
                        min_length=5,
                        max_length=50,
                        required=True
                    )

                    async def on_submit(self, interaction: discord.Interaction):
                        # Parse the member ID
                        member_input = self.member_id.value.strip()

                        # Extract ID from mention if needed
                        if member_input.startswith('<@') and member_input.endswith('>'):
                            member_input = member_input[2:-1]
                            if member_input.startswith('!'):
                                member_input = member_input[1:]

                        try:
                            member_id = int(member_input)
                            member = interaction.guild.get_member(member_id)

                            if not member:
                                await interaction.response.send_message(
                                    "❌ Could not find that member. Make sure they're in this server.", 
                                    ephemeral=True
                                )
                                return

                            # Check if member already has access to the ticket
                            existing_perms = interaction.channel.permissions_for(member)
                            if existing_perms.read_messages:
                                await interaction.response.send_message(
                                    f"❌ {member.mention} already has access to this ticket.", 
                                    ephemeral=True
                                )
                                return

                            # Add member to the ticket
                            await interaction.channel.set_permissions(
                                member,
                                read_messages=True,
                                send_messages=True,
                                attach_files=True,
                                embed_links=True
                            )

                            await interaction.response.send_message(
                                f"💖 {member.mention} has been added to the ticket by {interaction.user.mention}",
                            )

                        except ValueError:
                            await interaction.response.send_message(
                                "❌ Invalid member ID format. Please use a valid ID or mention.", 
                                ephemeral=True
                            )

                await interaction.response.send_modal(AddMemberModal())

        self.bot.add_view(TicketButtons())

        # Register the ApplicationButtons view for staff applications
        class ApplicationButtons(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)

            @discord.ui.button(label="Accept Application", emoji="✅", style=discord.ButtonStyle.success, custom_id="accept_application")
            async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Delegate to the full handler
                app_buttons = ApplicationButtonsWithHandlers(bot)
                await app_buttons.accept_application(interaction, button)

            @discord.ui.button(label="Reject Application", emoji="❌", style=discord.ButtonStyle.danger, custom_id="reject_application")
            async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Delegate to the full handler
                app_buttons = ApplicationButtonsWithHandlers(bot)
                await app_buttons.reject_application(interaction, button)

        self.bot.add_view(ApplicationButtons())

    async def register_persistent_views(self):
        """Register all persistent views used by the tickets cog"""
        # Register the ticket creation view
        self.bot.add_view(TicketView(self.bot))
        
        # Register the ticket management view
        class TicketButtons(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket")
            async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                ticket_handler = TicketButtonsWithHandlers(self.bot)
                await ticket_handler.handle_close(interaction, "closed")
                
            @discord.ui.button(label="Resolved", emoji="✅", style=discord.ButtonStyle.success, custom_id="resolve_ticket")
            async def resolve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                ticket_handler = TicketButtonsWithHandlers(self.bot)
                await ticket_handler.handle_close(interaction, "resolved")
                
            @discord.ui.button(label="Add Member", emoji="👤", style=discord.ButtonStyle.primary, custom_id="add_member")
            async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Add member handler code here
                pass
                
        self.bot.add_view(TicketButtons())
        
        # Register the application buttons view
        class ApplicationButtons(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(label="Accept Application", emoji="✅", style=discord.ButtonStyle.success, custom_id="accept_application")
            async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
                app_handler = ApplicationButtonsWithHandlers(self.bot)
                await app_handler.accept_application(interaction, button)
                
            @discord.ui.button(label="Reject Application", emoji="❌", style=discord.ButtonStyle.danger, custom_id="reject_application")
            async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
                app_handler = ApplicationButtonsWithHandlers(self.bot)
                await app_handler.reject_application(interaction, button)
                
        self.bot.add_view(ApplicationButtons())
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Tickets cog is ready")
        # Re-register the select menu view
        self.bot.add_view(TicketView(self.bot))
        logger.info("Re-registered ticket views")
        
        # Re-add ticket management views
        # Define view classes in-line similar to the __init__ method
        class TicketButtons(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)

            @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket")
            async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                ticket_button_view = TicketButtonsWithHandlers(self.bot)
                await ticket_button_view.handle_close(interaction, "closed")

            @discord.ui.button(label="Resolved", emoji="✅", style=discord.ButtonStyle.success, custom_id="resolve_ticket")
            async def resolve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                ticket_button_view = TicketButtonsWithHandlers(self.bot)
                await ticket_button_view.handle_close(interaction, "resolved")

            @discord.ui.button(label="Add Member", emoji="👤", style=discord.ButtonStyle.primary, custom_id="add_member")
            async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
                # This just opens a modal, actual permission checks happen there
                class AddMemberModal(discord.ui.Modal, title="Add Member to Ticket"):
                    member_id = discord.ui.TextInput(
                        label="Member ID or @mention",
                        placeholder="Enter member ID or @mention (e.g., 123456789012345678 or @username)",
                        min_length=5,
                        max_length=50,
                        required=True
                    )
                    async def on_submit(self, interaction: discord.Interaction):
                        # Permission checks will happen at the beginning of the method
                        with open('config.json', 'r') as f:
                            config = json.load(f)
                        guild_id = str(interaction.guild.id)
                        staff_role_ids = config["guilds"][guild_id]["staff_roles"]
                        if not any(role.id in [int(r) for r in staff_role_ids] for role in interaction.user.roles):
                            await interaction.response.send_message(
                                "❌ Only staff members can add users to tickets.", 
                                ephemeral=True
                            )
                            return
                        # Rest of the implementation will be handled by the original callback
                        # which gets triggered when the form is submitted

                await interaction.response.send_modal(AddMemberModal())
        
        # Add the ticket buttons view to the bot
        self.bot.add_view(TicketButtons())
        logger.info("Registered persistent TicketButtons for ticket management")
        
        # Re-add application buttons view
        class ApplicationButtons(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)

            @discord.ui.button(label="Accept Application", emoji="✅", style=discord.ButtonStyle.success, custom_id="accept_application")
            async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
                app_buttons = ApplicationButtonsWithHandlers(self.bot)
                await app_buttons.accept_application(interaction, button)

            @discord.ui.button(label="Reject Application", emoji="❌", style=discord.ButtonStyle.danger, custom_id="reject_application")
            async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
                app_buttons = ApplicationButtonsWithHandlers(self.bot)
                await app_buttons.reject_application(interaction, button)
                
        self.bot.add_view(ApplicationButtons())
        logger.info("Registered persistent ApplicationButtons for staff applications")
        
        # NOTE: These views don't need any message IDs to work. Discord matches
        # interactions to our code using the custom_ids of the components.
        # As long as the custom_ids match, the interactions will work correctly.

    @app_commands.command(name="setup", description="Setup the ticket system for your server")
    @app_commands.describe(
        ticket_channel="The channel where the ticket creation message will be sent",
        ticket_category="The category where ticket channels will be created",
        log_channel="The channel where ticket logs will be sent",
        trial_staff_role="The role to assign to accepted staff applications"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup(
        self, 
        interaction: discord.Interaction, 
        ticket_channel: discord.TextChannel,
        ticket_category: discord.CategoryChannel,
        log_channel: discord.TextChannel,
        trial_staff_role: discord.Role = None
    ):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Set up the staff roles selection
        class StaffRoleSelect(discord.ui.View):
            def __init__(self, bot, ticket_channel, ticket_category, log_channel, trial_staff_role):
                super().__init__(timeout=300)  # 5 minute timeout
                self.bot = bot
                self.ticket_channel = ticket_channel
                self.ticket_category = ticket_category
                self.log_channel = log_channel
                self.trial_staff_role = trial_staff_role
                self.selected_roles = []

                # Add the role select menu
                self.add_item(StaffRoleSelectMenu(max_values=10))

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅", custom_id="confirm")
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not self.selected_roles:
                    await interaction.response.send_message("❌ Please select at least one staff role.", ephemeral=True)
                    return

                # Save the configuration
                with open('config.json', 'r') as f:
                    config = json.load(f)

                guild_id = str(interaction.guild.id)
                if guild_id not in config["guilds"]:
                    config["guilds"][guild_id] = {}

                config["guilds"][guild_id]["ticket_channel_id"] = self.ticket_channel.id
                config["guilds"][guild_id]["ticket_category_id"] = self.ticket_category.id
                config["guilds"][guild_id]["ticket_log_channel_id"] = self.log_channel.id
                config["guilds"][guild_id]["staff_roles"] = self.selected_roles
                if self.trial_staff_role:
                    config["guilds"][guild_id]["trial_staff_role_id"] = self.trial_staff_role.id

                with open('config.json', 'w') as f:
                    json.dump(config, f, indent=4)

                # Send the ticket creation message
                ticket_message = get_message_from_template("ticket_create", {
                    "server_name": interaction.guild.name,
                    "timestamp": int(datetime.now().timestamp())
                })

                await self.ticket_channel.send(
                    content=ticket_message["content"],
                    embeds=ticket_message["embeds"],
                    view=TicketView(self.bot)
                )

                await interaction.response.send_message(
                    "✅ Ticket system has been set up successfully! The ticket creation message has been sent.", 
                    ephemeral=True
                )

                self.stop()

        class StaffRoleSelectMenu(discord.ui.Select):
            def __init__(self, max_values=10):
                options = []

                # Get all roles that can be selected as staff roles
                roles = sorted(
                    [r for r in interaction.guild.roles if r.name != "@everyone" and not r.is_default()],
                    key=lambda r: r.position,
                    reverse=True
                )

                # Limit to 25 roles (Discord max)
                roles = roles[:25]

                for role in roles:
                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=str(role.id),
                            description=f"Position: {role.position}"
                        )
                    )

                super().__init__(
                    placeholder="Select staff roles...",
                    min_values=1,
                    max_values=min(max_values, len(options)),
                    options=options
                )

            async def callback(self, interaction: discord.Interaction):
                view = self.view
                if isinstance(view, StaffRoleSelect):
                    view.selected_roles = self.values

                    role_names = []
                    for role_id in self.values:
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            role_names.append(role.name)

                    await interaction.response.send_message(
                        f"✅ Selected roles: {', '.join(role_names)}\nClick Confirm to finish setup.",
                        ephemeral=True
                    )

        # Start the setup process
        view = StaffRoleSelect(self.bot, ticket_channel, ticket_category, log_channel, trial_staff_role)

        # Send the setup message
        setup_message = get_message_from_template("staff_setup", {
            "server_name": interaction.guild.name,
            "timestamp": int(datetime.now().timestamp())
        })

        await interaction.followup.send(
            content=setup_message["content"],
            embeds=setup_message["embeds"],
            view=view,
            ephemeral=True
        )

    @app_commands.command(name="sendticket", description="Send the ticket creation message to a channel")
    @app_commands.describe(channel="The channel to send the ticket creation message to")
    @app_commands.default_permissions(administrator=True)
    async def sendticket(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        # Load config
        with open('config.json', 'r') as f:
            config = json.load(f)

        guild_id = str(interaction.guild.id)

        # Check if the guild has been set up
        if guild_id not in config["guilds"] or not config["guilds"][guild_id]["ticket_category_id"]:
            await interaction.response.send_message(
                "❌ Ticket system hasn't been set up for this server yet. Please use /setup first.", 
                ephemeral=True
            )
            return

        # Use provided channel or default to the configured ticket channel
        if not channel:
            channel_id = config["guilds"][guild_id]["ticket_channel_id"]
            channel = interaction.guild.get_channel(int(channel_id))

            if not channel:
                await interaction.response.send_message(
                    "❌ The configured ticket channel no longer exists. Please use /setup again.", 
                    ephemeral=True
                )
                return

        # Send the ticket creation message
        await interaction.response.defer(ephemeral=True)

        ticket_message = get_message_from_template("ticket_create", {
            "server_name": interaction.guild.name,
            "timestamp": int(datetime.now().timestamp())
        })

        await channel.send(
            content=ticket_message["content"],
            embeds=ticket_message["embeds"],
            view=TicketView(self.bot)
        )

        await interaction.followup.send(
            f"✅ Ticket creation message has been sent to {channel.mention}.", 
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Tickets(bot))
