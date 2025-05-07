import discord 
from discord import app_commands
from discord.ext import commands 
from utilities import Permissions, colors, get_all_variables, get_emojis_variables, get_message_from_template
from utilities import send_log, send_notif, get_link, format_time
import asyncio
from errors.error_logger import error_send
from typing import List
import sqlite3 
import datetime
import time
from utilities import load_roles_ids
import json

class ServerLinkView(discord.ui.View):
    def __init__(self, guild_name, channel_link):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label=f"Sent from {guild_name}", 
            url=channel_link, 
            style=discord.ButtonStyle.link
        ))
  
class ReportActionView(discord.ui.View):
    def __init__(self, bot, target: discord.Member, reporter: discord.User, timeout=None):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.target = target
        self.reporter = reporter
        
        self.link_view = ServerLinkView(target.guild.name, f"https://discord.com/channels/{target.guild.id}")
        self.response_embed = discord.Embed(title="Report Received – Thank You for Your Support", description="Thank you for your report. Our team has reviewed it and is taking the appropriate action. While we cannot disclose specific details regarding the outcome, we truly appreciate your effort in helping us maintain a safe and respectful community by reporting rule violations.", color=colors.primary)
        self.response_embed.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport5.png")
        self.response_embed.set_author(name=target.guild.name, url=f"https://discord.com/channels/{target.guild.id}", icon_url=target.guild.icon.url if target.guild.icon else None)
     
    
    async def disable(self, interaction):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = colors.green
        await interaction.message.edit(embed=embed, view=self)


    @discord.ui.button(label="Warn and timeout", style=discord.ButtonStyle.primary, custom_id="report_timeout")
    async def timeout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message(f"**Click: </warn add:1361075068939276532>**", ephemeral=True)
            await self.reporter.send(embed=self.response_embed, view=self.link_view)
            await self.disable(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Failed to timeout: {e}", ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.danger, custom_id="report_kick")
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message(f"**Click </kick:678344927997853742>**", ephemeral=True)
            await self.reporter.send(embed=self.response_embed, view=self.link_view)
            await self.disable(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Failed to kick: {e}", ephemeral=True)

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, custom_id="report_ban")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message(f"**Click </ban:1350827584488869971>**", ephemeral=True)
            await self.reporter.send(embed=self.response_embed, view=self.link_view)
            await self.disable(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Failed to ban: {e}", ephemeral=True)

    @discord.ui.button(label="Pass", style=discord.ButtonStyle.secondary, custom_id="report_respond")
    async def respond_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message("Responded to the reporter.", ephemeral=True)
            await self.reporter.send(embed=self.response_embed, view=self.link_view)
            await self.disable(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Could not message reporter: {e}", ephemeral=True)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.delete_delay = 5
        self.conn = sqlite3.connect("database/data.db")
        self.create_table()
        self.reports_channel_id = 1361091376162410547
    
    
    @commands.Cog.listener()
    async def on_ready(self):
        with open("./configs/channels/channels_id.json", "r") as f:
            data = json.load(f)
        for guild in self.bot.guilds:
            self.reports_channel_id = data.get(str(guild.id), {}).get("reports_channel_id", None)
    
    def create_table(self):
        cur = self.conn.cursor()
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS configs (
                guild_id INTEGER PRIMARY KEY,
                jail_role_id INTEGER,
                sus_role_id INTEGER
            )""")
            self.conn.commit()
        finally:
            cur.close()
    
    def get_roles(self, guild_id: int):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT jail_role_id, sus_role_id FROM configs WHERE guild_id = ?", (guild_id,))
            result = cur.fetchone()
            if result:
                jail_role_id, sus_role_id = result
                return jail_role_id, sus_role_id
            else:
                return None, None
        finally:
            cur.close()
    
    def upsert_config(self, guild_id: int, column: str, value: int):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT 1 FROM configs WHERE guild_id = ?", (guild_id,))
            exists = cur.fetchone()
            if exists:
                cur.execute(f"UPDATE configs SET {column} = ? WHERE guild_id = ?", (value, guild_id))
            else:
                cur.execute(f"INSERT INTO configs (guild_id, {column}) VALUES (?, ?)", (guild_id, value))
            self.conn.commit()
        finally:
            cur.close()
    
    async def check_perm(self, interaction, user_perms: List, bot_perms: List, target: discord.Member = None):
        permissions = Permissions(interaction)
        return await permissions.check_perm(user_perms, bot_perms, target)
    
    def is_image(self, proof: discord.Attachment) -> bool:
        return proof.content_type.startswith('image/')
        
    #  _______________________ Jail Commands  _______________________ 
    jail_group = app_commands.Group(name="jail", description="Jail related commands")
    @jail_group.command(name="role", description="Jail a member.")
    @app_commands.describe(role="Jail role. If you don't have one do '/jail setup'")
    async def jailrole(self, interaction: discord.Interaction, role: discord.Role):
        try:
            authorized = await self.check_perm(interaction, ["administrator"], ["manage_roles"])
            if not authorized:
                return 
            if role.position >= interaction.guild.me.top_role.position:
                response_embed = discord.Embed(description="That role is higher than my top role. The role should be under mine so i can assign it to offenders.", color=colors.forbidden)
                await interaction.response.send_message(embed=response_embed, ephemeral=True)
                return 
            self.upsert_config(interaction.guild.id, "jail_role_id", role.id)
            response_embed = discord.Embed(title="Set up finished!", description=f"{role.name} have been set successfully!", color=colors.primary)
            await interaction.response.send_message(embed=response_embed)
        except Exception:
            await error_send(interaction)
    
    @jail_group.command(name="setup", description="setup a jail role automatically")
    async def createjail(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            authorized = await self.check_perm(interaction, ["administrator"], ["manage_roles"])
            if not authorized:
                return 
            response_embed = discord.Embed(title="Setting Up", description="Creating and setting up jail is in progress..", color=colors.primary)
            original_response = await interaction.followup.send(embed=response_embed, ephemeral = False)
            # Creatuing role
            guild = interaction.guild
            role: discord.Role
            try: 
                role = await guild.create_role(name="Jailed", color=0xec1a1a)
                self.upsert_config(guild.id, "jail_role_id", role.id)
            except discord.Forbidden:
                response_embed.description = "I don't have permission to create roles. make sure to give me manage roles permission."
                await original_response.edit(embed=response_embed)
                return 
            # Get bot top role position 
            highest_role = max((role for role in guild.roles if role < guild.me.top_role), key=lambda r: r.position)
            # move role right below the bot highest role 
            if highest_role:
                await role.edit(position=highest_role.position)
            # loop through all channels and add permissions restrictions for the role 
            for category in guild.categories:
                overwrites = category.overwrites_for(role)
                overwrites.view_channel = False
                try:
                    await category.set_permissions(role, overwrite=overwrites)
                except discord.Forbidden:
                    response_embed.description = f"Failed to set restrictions for jail role in {category.name} due to lack of permissions. (Skipped)"
                    await original_response.edit(embed=response_embed)
                    await asyncio.sleep(5)
                    continue
            
                for channel in category.channels:
                    if not channel.permissions_synced:
                        overwrites = channel.overwrites_for(role)
                        if isinstance(channel, discord.TextChannel):
                            overwrites.view_channel = False
                            overwrites.send_messages = False
                        elif isinstance(channel, discord.VoiceChannel):
                            overwrites.view_channel = False
                            overwrites.connect = False
                            overwrites.speak = False
                        try:
                            await channel.set_permissions(role, overwrite=overwrites)
                        except discord.Forbidden:
                            response_embed.description = f"Failed to set restrictions for jail role in {channel.mention} due to lack of permissions. (Skipped)"
                            await original_response.edit(embed=response_embed)
                            await asyncio.sleep(5)
                            continue
            
            response_embed.title = "Set up finished!"
            response_embed.description = f"Setting up {role.mention} has been successfully finished!"
            await original_response.edit(embed=response_embed)
            await interaction.followup.send(f"{interaction.user.mention} setting up the role is finished and added as the main jail role!")
        except Exception:
            await error_send(interaction)

    @jail_group.command(name="add", description="Jail a member.")
    @app_commands.describe(member="Target member.", reason="Why are they getting jailed? what did they do?", proof="Do you have a proof against them?")
    async def jail(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment):
        try:
            # Check permissions
            authorized = await self.check_perm(interaction, user_perms = ["moderate_members"], bot_perms = ["manage_roles"], target = member)
            if not authorized:
                return 
            # Check proof type 
            if proof and not self.is_image(proof):
                embed = discord.Embed(title="Input Error", description="The proof must be an image file, not a video or other type.", color=colors.forbidden)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            # get jail role 
            guild = interaction.guild
            role_id = None
            # get role from database 
            cur = self.conn.cursor()
            try:
                cur.execute("SELECT jail_role_id FROM configs WHERE guild_id = ?", (guild.id,))
                result = cur.fetchone()
                role_id = result[0] if result else None
                self.conn.commit()
            finally:
                cur.close()
            # in case there's no role in database for that server 
            if not role_id or not discord.utils.get(guild.roles, id=role_id):
                not_found_embed = discord.Embed(title="Not found", description="There's no jail role found.\n`/jail role`: To add a jail role if you already have one in the server.\n`/jail create`: If you don't have a jail role do this command to setup one automatically.", color=colors.forbidden)
                await interaction.response.send_message(embed=not_found_embed, ephemeral=True)
                return 
            # fetch role 
            role = discord.utils.get(guild.roles, id=role_id)
            # check if user already jailed 
            if role in member.roles:
                response_embed = discord.Embed(title="Forbidden", description=f"{member.mention} is jailed already.", color=colors.forbidden)
                await interaction.response.send_message(embed=response_embed, ephemeral=True)
                return 
            # Add role to user
            await member.add_roles(role, reason=f"{reason} | Responsible: {interaction.user.name}")
            # respond back
            response_embed = discord.Embed(title="Member Jailed!", description=f"{member.mention} Has been jailed successfully!", color=colors.primary)
            await interaction.response.send_message(embed=response_embed, ephemeral=False, delete_after=self.delete_delay)
            # logging
            proof_url = None
            if proof:
                proof_url = await get_link(proof)
            variables = get_all_variables(member, guild, interaction.user)
            variables.update({"reason": reason})
            variables.update({"proofurl": proof_url if proof_url else ""})
            await send_log(self.bot, variables, "log_jail")
            await send_notif(member, variables, "notif_jail")
        except Exception:
            await error_send(interaction)
    
    @jail_group.command(name="remove", description="Unjail a user.")
    @app_commands.describe(member="Target member.", reason="Why are they getting Unjailed? did they verify themselves?", proof="Do you have a proof you want to provide?")
    async def unjail(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment):
        try:
            authorized = await self.check_perm(interaction, user_perms = ["moderate_members"], bot_perms = ["manage_roles"], target = member)
            if not authorized:
                return 
            # Check proof type 
            if proof and not self.is_image(proof):
                embed = discord.Embed(title="Input Error", description="The proof must be an image file, not a video or other type.", color=colors.forbidden)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            # Jailing process 
            role_id: int
            guild = interaction.guild
            # Get role from database 
            cur = self.conn.cursor()
            try:
                cur.execute("SELECT jail_role_id FROM configs WHERE guild_id = ?", (guild.id,))
                result = cur.fetchone()
                role_id = result[0] if result else None
                self.conn.commit()
            finally:
                cur.close()
            # fetch role 
            not_found_embed = discord.Embed(title="Not found", description="There's no jail role found.\n`/jail role`: To add a jail role if you already have one in the server.\n`/jail create`: If you don't have a jail role do this command to setup one automatically.", color=colors.forbidden)
            if not role_id:
                await interaction.response.send_message(embed=not_found_embed, ephemeral=True)
                return 
            role = discord.utils.get(guild.roles, id=role_id)
            if not role:
                await interaction.response.send_message(embed=not_found_embed, ephemeral=True)
                return 
            if any(user_role.id == role.id for user_role in member.roles):
                await member.remove_roles(role, reason = f"{reason} | Responsible: {interaction.user.name}")
                response_embed = discord.Embed(title="Unjailed Successfully!", description=f"{member.mention} is Unjailed.", color=colors.primary)
                await interaction.response.send_message(embed=response_embed, ephemeral=False, delete_after=self.delete_delay)
            else:
                response_embed = discord.Embed(title="Failed!", description=f"{member.mention} is not jailed to be unjailed.", color=colors.forbidden)
                await interaction.response.send_message(embed=response_embed, ephemeral=True)
                return 
            proof_url = None
            if proof:
                proof_url = await get_link(proof)
            variables = get_all_variables(member, interaction.guild, interaction.user)
            variables.update({"reason": reason})
            variables.update({"proofurl": proof_url if proof_url else ""})
            await send_log(self.bot, variables, "log_unjail")
            await send_notif(member, variables, "notif_unjail")
        except Exception:
            await error_send(interaction)

    #  _______________________ Sus Commands  _______________________ 
    sus_group = app_commands.Group(name="sus", description="Sus related commands")
    @sus_group.command(name="setup", description="Make sus role for you.")
    async def sus_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            authorized = await self.check_perm(interaction, ["administrator"], ["manage_roles"])
            if not authorized:
                return 
            # set up the role
            guild = interaction.guild
            role = None
            response_embed = discord.Embed(title="Setting Up", description="Creating and setting up sus role is in progress..", color=colors.primary)
            cur = self.conn.cursor()
            try: 
                cur.execute("SELECT sus_role_id FROM configs WHERE guild_id = ?", (guild.id,))
                result = cur.fetchone()
                self.conn.commit()
                role = discord.utils.get(guild.roles, id=result[0]) if result else None
                if not role:
                    role = await guild.create_role(name="Sus", color=0xfa0606)
                    self.upsert_config(guild.id, "sus_role_id", role.id)
            except discord.Forbidden:
                response_embed.description = "I don't have permission to create roles. make sure to give me manage roles permission."
                await interaction.followup.send(embed=response_embed)
                return 
            finally:
                cur.close()
            # Get bot top role position 
            highest_role = max((role for role in guild.roles if role < guild.me.top_role), key=lambda r: r.position)
            # move role right below the bot highest role 
            if highest_role:
                await role.edit(position=highest_role.position - 1)
            guide = (f"""
I've already created the {role.mention} role, but the rest of the setup needs to be done manually. Here's a simple guide to help you:

1. Go to each channel where you **don't** want suspicious users to have access.  
2. **Hold-click** on the channel → **Edit Channel** → **Permissions**.  
3. Click **Add Role** and select {role.mention}.  
4. Under **Permissions**, disable the following:  
   - **View Channels** = ❌  
   - **Send Messages** = ❌  
5. (Optional) Adjust other permissions as needed. If you want to **completely hide** the channel from them, ensure both settings above are disabled.  

That's it! Now, suspicious users won't be able to see or interact in those channels.
            """)
            guide_embed = discord.Embed(title="Sus Role Setup", description=guide, color=colors.primary)
            guide_embed.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/guides/channelperm.gif")
            await interaction.followup.send(embed=guide_embed, ephemeral=True)
        except Exception:
            await error_send(interaction)
    
    @sus_group.command(name="role", description="Setup sus role if available otherwise do `/sus setup`")
    async def sus_role(self, interaction: discord.Interaction, role: discord.Role):
        try:
            authorized = await self.check_perm(interaction, ["administrator"], ["manage_roles"])
            if not authorized:
                return 
            guild = interaction.guild
            if role.position >= guild.me.top_role.position:
                response_embed = discord.Embed(description="That role is higher than my top role. The role should be under mine so i can assign it to offenders.", color=colors.forbidden)
                await interaction.response.send_message(embed=response_embed, ephemeral=True)
                return 
            # Save role in database 
            self.upsert_config(guild.id, "sus_role_id", role.id)
            # respond to user
            embed = discord.Embed(title="Role Have been set", description=f"{role.mention} was set as a sus role!", color = colors.primary)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            await error_send(interaction)
    
    @sus_group.command(name="add", description="Add suspicious role to a specific member.")
    @app_commands.describe(member="Target member.", reason="Why are they suspicious? what did they do?", proof="Do you have a proof against them?")
    async def sus(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment):
        try:
            authorized = await self.check_perm(interaction, ["moderate_members"], ["manage_roles"])
            if not authorized:
                return 
            # Check proof type 
            if proof and not self.is_image(proof):
                embed = discord.Embed(title="Input Error", description="The proof must be an image file, not a video or other type.", color=colors.forbidden)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            guild = interaction.guild
            role_id = None
            cur = self.conn.cursor()
            try:
                cur.execute("SELECT sus_role_id FROM configs WHERE guild_id = ?", (guild.id,))
                result = cur.fetchone()
                role_id = result[0] if result else None
                self.conn.commit()
            finally:
                cur.close()
            if not role_id and not discord.utils.get(guild.roles, id = role_id):
                response_embed = discord.Embed(title="Not Found", description="No Sus role found, do `/sus setup` to setup one, or `/sus role` to set a sus role if you already have one.", color=colors.forbidden)
                await interaction.response.send_message(embed=response_embed, ephemeral=True)
                return 
            role = discord.utils.get(guild.roles, id = role_id)
            if role in member.roles:
                response_embed = discord.Embed(title="Forbidden", description=f"{member.mention} is suspected already.", color=colors.forbidden)
                await interaction.response.send_message(embed=response_embed, ephemeral=True)
                return 
            await member.add_roles(role, reason=f"{reason} | Responsible: {interaction.user.name}")
            response_embed = discord.Embed(title="Member Was Suspected!", description=f"{member} Has been suspected.", color=colors.primary)
            await interaction.response.send_message(embed=response_embed, delete_after=self.delete_delay)
            proof_url = None
            if proof:
                proof_url = await get_link(proof)
            variables = get_all_variables(member, guild, interaction.user)
            variables.update({"reason": reason})
            variables.update({"proofurl": proof_url if proof_url else ""})
            await send_log(self.bot, variables, "log_sus")
            await send_notif(member, variables, "notif_sus")
        except Exception:
            await error_send(interaction)
    
    @sus_group.command(name="remove", description="Remove suspicious role from a specific member.")
    @app_commands.describe(member="Target member.", reason="Why are they getting unsus? did they verify?", proof="Do you have a proof against them?")
    async def unsus(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment):
        try:
            authorized = await self.check_perm(interaction, ["moderate_members"], ["manage_roles"])
            if not authorized:
                return 
            # Check proof type 
            if proof and not self.is_image(proof):
                embed = discord.Embed(title="Input Error", description="The proof must be an image file, not a video or other type.", color=colors.forbidden)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            guild = interaction.guild
            role_id = None
            cur = self.conn.cursor()
            try:
                cur.execute("SELECT sus_role_id FROM configs WHERE guild_id = ?", (guild.id,))
                result = cur.fetchone()
                role_id = result[0] if result else None
                self.conn.commit()
            finally:
                cur.close()
                
            if not role_id and not discord.utils.get(guild.roles, id = role_id):
                response_embed = discord.Embed(title="Not Found", description="No Sus role found, do `/sus setup` to setup one, or `/sus role` to set a sus role if you already have one.", color=colors.forbidden)
                await interaction.response.send_message(embed=response_embed, ephemeral=True)
                return 
            
            role = discord.utils.get(guild.roles, id = role_id)
            if role not in member.roles:
                response_embed = discord.Embed(title="Forbidden", description=f"{member.mention} is no suspected.", color=colors.forbidden)
                await interaction.response.send_message(embed=response_embed, ephemeral=True)
                return 
            
            await member.remove_roles(role, reason=f"{reason} | Responsible: {interaction.user.name}")
            
            response_embed = discord.Embed(title="Member Was unsuspected!", description=f"{member} Has been unsuspected.", color=colors.primary)
            await interaction.response.send_message(embed=response_embed, delete_after=self.delete_delay)
            proof_url = None
            if proof:
                proof_url = await get_link(proof)
            variables = get_all_variables(member, guild, interaction.user)
            variables.update({"reason": reason})
            variables.update({"proofurl": proof_url if proof_url else ""})
            await send_log(self.bot, variables, "log_unsus")
            await send_notif(member, variables, "notif_unsus")
        except Exception:
            await error_send(interaction)
    
    
    #  _______________________ Warn Commands  _______________________
    async def warn_handler(self, interaction: discord.Interaction, member: discord.Member, timeout: app_commands.Choice[int], reason: str, proof: discord.Attachment):
        try:
            await interaction.response.defer()
            # Check permissions
            authorized = await self.check_perm(interaction, user_perms = ["moderate_members"], bot_perms = ["manage_roles", "moderate_members"], target = member)
            if not authorized:
                return
            # check proof validation 
            if proof and not self.is_image(proof):
                embed = discord.Embed(title="Input Error", description="The proof must be an image file, not a video or other type.", color=colors.forbidden)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            # get warn roles
            guild = interaction.guild
            warn_roles = {}
            warns_number = 0
            # check how many warn do user has
            for i in range(1,4):
                warn_role = discord.utils.get(guild.roles, name=f"warn ({i})")
                if not warn_role:
                    warn_role = await guild.create_role(name=f"warn ({i})", color=0xe71212, reason="Creating warn roles for the first time.")
                warn_roles[i] = warn_role
            for i in range(1,4):
                if warn_roles[i] in member.roles:
                    warns_number += 1
                    if warn_roles[i].name == "warn (3)":
                        await member.ban(reason="Too many warnings.")
                        break
                else:
                    await member.add_roles(warn_roles[i], reason=f"warned | Responsible: {interaction.user.name}")
                    break 
            
            # apply timeout
            if timeout.value != 0:
                await member.timeout(datetime.timedelta(seconds=timeout.value), reason=reason)
            
            # respond to user
            warns_left = 3 - warns_number
            variables = get_all_variables(member, guild, interaction.user)
            variables.update({"warnsleft": warns_left})
            formated_duration = format_time(timeout.value)
            variables.update({"duration": formated_duration})
            variables.update({"reason": reason})
            respond_embed = discord.Embed(title="Member Warned", description="{membermention} has been warned!\n{emoji_reason} **Reason:** {reason} ({warnsleft} left)\n{emoji_timeout} **Duration:** {duration}".format(**variables), color=colors.primary)
            response = await interaction.followup.send(embed=respond_embed)
            sent_time = time.time()
            # logs and notification 
            proof_url = None
            if proof:
                proof_url = await get_link(proof)
            variables.update({"proofurl": proof_url if proof_url else ""})
            await send_log(self.bot, variables, "log_warn")
            await send_notif(member, variables, "notif_warn")
            await asyncio.sleep(max(0, self.delete_delay - (time.time() - sent_time)))
            try:
                await response.delete()
            except discord.NotFound:
                pass
        except Exception:
            await error_send(interaction)
    async def unwarn_handler(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment):
        try:
            await interaction.response.defer(ephemeral=False)
            authorized = await self.check_perm(interaction, ["moderate_members"], ["moderate_members", "manage_roles"], target = member)
            if not authorized:
                return 
            guild = interaction.guild
            warn_roles = {}
            for i in range(1,4):
                warn_role = discord.utils.get(guild.roles, name=f"warn ({i})")
                warn_roles[i] = warn_role
            
            user_warn = 0
            for i, role in warn_roles.items():
                if role in member.roles:
                    user_warn += 1
            
            if user_warn > 0:
                role_to_remove = warn_roles.get(user_warn)
                if role_to_remove:
                    await member.remove_roles(role_to_remove, reason=f"Unwarn | Responsible: {interaction.user.name}")
            await member.timeout(datetime.timedelta(0), reason=f"Unwarn | Responsible: {interaction.user.name}")
            
          
            variables = get_all_variables(member, guild, interaction.user)
            variables.update({"reason": reason})
            respond_embed = discord.Embed(title="Member Unwarned", description="{membermention} has been unwarned!\n{emoji_reason} **Reason:** {reason}".format(**variables), color=colors.primary)
            response = await interaction.followup.send(embed=respond_embed, ephemeral=False)
            sent_time = time.time()
            # logs and notification 
            proof_url = None
            if proof:
                proof_url = await get_link(proof)
            variables.update({"proofurl": proof_url if proof_url else ""})
            await send_log(self.bot, variables, "log_unwarn")
            await send_notif(member, variables, "notif_unwarn")
            await asyncio.sleep(max(0, self.delete_delay - (time.time() - sent_time)))
            try:
                await response.delete()
            except discord.NotFound:
                pass
        except Exception:
            await error_send(interaction)
           
    warn_group = app_commands.Group(name="warn", description="Warn/Unwarn a member with timeout if needed.")
    @warn_group.command(name="add", description="Add a warning to a member.")
    @app_commands.choices(timeout=[
        app_commands.Choice(name="No timeout needed.", value=0),
        app_commands.Choice(name="5 minute", value=300),
        app_commands.Choice(name="10 minutes", value=600),
        app_commands.Choice(name="1 hour", value=3600),
        app_commands.Choice(name="6 hours", value=21600),
        app_commands.Choice(name="12 hours", value=43200),
        app_commands.Choice(name="1 day", value=86400),
        app_commands.Choice(name="2 days", value=172800),
        app_commands.Choice(name="3 days", value=259200),
        app_commands.Choice(name="4 days", value=345600),
        app_commands.Choice(name="5 days", value=432000),
        app_commands.Choice(name="6 days", value=518400),
        app_commands.Choice(name="7 days", value=604800),
        app_commands.Choice(name="15 days", value=1296000),
        app_commands.Choice(name="20 days", value=1728000),
        app_commands.Choice(name="30 days", value=2419200)
    ])
    @app_commands.describe(member="Target member.", timeout="Add a timeout to member.", reason="For what reason are they getting warned?", proof="Attach screenshots as proof.")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, timeout: app_commands.Choice[int], reason: str, proof: discord.Attachment):
        await self.warn_handler(interaction, member, timeout, reason, proof)
    
    @warn_group.command(name="remove", description="Remove a warning from a member.")
    async def unwarn(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment):
        await self.unwarn_handler(interaction, member, reason, proof)
    
    #  _______________________ Warn Commands  _______________________
    mute_group = app_commands.Group(name="mute", description="mute/unmute a member with timeout if needed.")
    @mute_group.command(name="add", description="Add a mute to a member.")
    @app_commands.choices(timeout=[
        app_commands.Choice(name="5 minute", value=300),
        app_commands.Choice(name="10 minutes", value=600),
        app_commands.Choice(name="1 hour", value=3600),
        app_commands.Choice(name="6 hours", value=21600),
        app_commands.Choice(name="12 hours", value=43200),
        app_commands.Choice(name="1 day", value=86400),
        app_commands.Choice(name="2 days", value=172800),
        app_commands.Choice(name="3 days", value=259200),
        app_commands.Choice(name="4 days", value=345600),
        app_commands.Choice(name="5 days", value=432000),
        app_commands.Choice(name="6 days", value=518400),
        app_commands.Choice(name="7 days", value=604800),
        app_commands.Choice(name="15 days", value=1296000),
        app_commands.Choice(name="20 days", value=1728000),
        app_commands.Choice(name="30 days", value=2419200)
    ])
    @app_commands.describe(member="Target member.", timeout="Add a timeout to member.", reason="For what reason are they getting muted?", proof="Attach screenshots as proof.")
    async def mute(self, interaction: discord.Interaction, member: discord.Member, timeout: app_commands.Choice[int], reason: str, proof: discord.Attachment):
        await self.warn_handler(interaction, member, timeout, reason, proof)
        
    @mute_group.command(name="remove", description="Remove a timeout from a member.")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment):
        await self.unwarn_handler(interaction, member, reason, proof)
    
    
    
    #  _______________________ Verification Commands  _______________________
    verify = app_commands.Group(name="verify", description="Verification commands.")
    @verify.command(name="add", description="Verify a member.")
    @app_commands.choices(
        gender = [
            app_commands.Choice(name="Female", value="female"),
            app_commands.Choice(name="Male", value="male"),
            app_commands.Choice(name="Trans Male", value="transM"),
            app_commands.Choice(name="Trans Female", value="transF"),
            app_commands.Choice(name="Non-binary", value="none"),
        ]
    )
    @app_commands.choices(
        age = [
            app_commands.Choice(name="18 years old", value="age18"),
            app_commands.Choice(name="19 years old", value="age19"),
            app_commands.Choice(name="20 years old", value="age20"),
            app_commands.Choice(name="21 years old", value="age21"),
            app_commands.Choice(name="22 years old", value="age22"),
            app_commands.Choice(name="23 years old", value="age23"),
            app_commands.Choice(name="24 years old", value="age24"),
            app_commands.Choice(name="25+ years old", value="age25")
        ]
    )
    @app_commands.describe(member="Who is the member you are trying to verify?", gender="What is their gender?", age="What is their age?", proof="Show a proof of their verification (e.g screenshot)")
    async def verify_cmd(self, interaction: discord.Interaction, member: discord.Member, gender: app_commands.Choice[str], age: app_commands.Choice[str], proof: discord.Attachment):
        try:
            await interaction.response.defer(ephemeral=True)
            authorized = await self.check_perm(interaction, ["moderate_members"], ["manage_roles"])
            if not authorized:
                return 
            
            if member == interaction.user:
                await interaction.followup.send("I'm not gonna to allow you to verify yourself duh 🙄 ", ephemeral=True)
            if member.bot:
                await interaction.followup.send("You can't verify a bot duh 🙄 ", ephemeral=True)
                
            
            guild = interaction.guild
            gender_roles_ids = load_roles_ids("gender_roles", guild.id)
            age_roles_ids = load_roles_ids("age", guild.id)
            issues = []
            
            gender_role = discord.utils.get(guild.roles, id=gender_roles_ids[gender.value])
            if gender_role:
                # remove any other gender roles from user if exists 
                for role in member.roles:
                    if role.id in gender_roles_ids.values() and role.id != gender_role.id:
                        await member.remove_roles(role, reason="Verification; roles replacement.")
                # add the correct gender role if not exists 
                if gender_role not in member.roles:
                    await member.add_roles(gender_role, reason="Verification; gender role.")
            else:
                issues.append(f"!! • {gender.value} role not found.")
            
            age_role = discord.utils.get(guild.roles, id=age_roles_ids[age.value])
            if age_role:
                for role in member.roles:
                    if role.id in age_roles_ids.values() and role.id != age_role.id:
                        await member.remove_roles(role, reason="Verification; roles replacement.")
                if age_role not in member.roles:
                    await member.add_roles(age_role, reason="Verification; age role.")
            else:
                issues.append(f"!! • {age.value} role not found.")
            
            verified_roles = load_roles_ids("verified_roles", guild.id)
            verified_role = discord.utils.get(guild.roles, id=verified_roles[gender.value])
            
            if not verified_role:
                embed = discord.Embed(title="<:forbidden:1359820382177198308> Error", description=f"verified {gender.value} role is not found! member can't be verified.\nReport this to Simo.", color=colors.error)
                if issues:
                    embed.add_feild(name="<:warn:1359816466513526885> Other issues:", value="\n".join(issues))
                await interaction.followup.send(embed=embed, ephemeral=True)
                return 
            
            # Check in case the user have already the opposite gender verification role
            for role in member.roles:
                if role.id in verified_roles.values() and role.id != verified_role.id:
                    await member.remove_roles(role, reason="Remove previous verification roles. prolly assigned by mistake.")
             
            await member.add_roles(verified_role, reason="Verified member role added!")
            
            # Remove jail/sus roles if exists 
            jail_role_id, sus_role_id = self.get_roles(guild.id)
            sus_role = None
            jail_role = None
            if jail_role_id:
                sus_role = discord.utils.get(guild.roles, id=int(sus_role_id))
            if sus_role_id:
                jail_role = discord.utils.get(guild.roles, id=int(jail_role_id))
            # get variables 
            variables = get_all_variables(member, guild, interaction.user)
            
            if sus_role:
                if sus_role in member.roles:
                    await send_notif(member, variables, "notif_unsus")
                    await member.remove_roles(sus_role, reason="Remove previous verification roles. prolly assigned by mistake.")
            if jail_role:
                if jail_role in member.roles:
                    await send_notif(member, variables, "notif_unjail")
                    await member.remove_roles(jail_role, reason="Remove previous verification roles. prolly assigned by mistake.")
            
            # response 
            embed = discord.Embed(title="<a:TwoHearts:1359827390616047726> Verified Successfully!", description=f"<a:Heartribbon:1359828243947061339> {member.mention} Was verified successfully!", color=colors.primary)
            if issues:
                embed.add_feild(name="<:warn:1359816466513526885> Other issues:", value="\n".join(issues))
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # logs and notification 
            proof_url = None
            if proof:
                proof_url = await get_link(proof)
            variables.update({"proofurl": proof_url if proof_url else ""})
            # send log
            await send_log(self.bot, variables, "log_verified")
            await send_notif(member, variables, "notif_verified")
        except Exception:
            await error_send(interaction)
    
    
    #  _______________________ Verification Commands  _______________________
    @app_commands.command(name="report", description="Quick report a user.")
    @app_commands.describe(member="The target member you want to report.", reason="What did they do?", proof="Upload a screenshot of what they did.", message_link="Link of the message. (hold click on the message then copy link.)")
    async def quick_report(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment, message_link: str = None):
        try:
            await interaction.response.defer(ephemeral=True)
            reporter = interaction.user
            
            if reporter == member:
                await interaction.followup.send("Why would you report yourself? 😭🙏")
                return 
            
            if member.id == self.bot.user.id:
                await interaction.followup.send("Nice try bit I'm the dominant here 😏 you cannot report ne sweetie.")
                return 
            
            if member.bot:
                await interaction.followup.send("You cannot report a bot 😔")
                return 
            
            channel = self.bot.get_channel(self.reports_channel_id)
            if not channel:
                await interaction.followup.send("Opps, haha do sorry 😅 there's a technical issue, please reach the support through support channel in the server.")
                return 
            
            var = get_all_variables(member, interaction.guild, reporter)
            var.update({"reason": reason})
            var.update({"proof_url": proof.url})
            var.update({"message_link": message_link if message_link else "Not provided"})
            message_data = get_message_from_template("notif_report", var)
            view = ReportActionView(self.bot, member, reporter)
            await channel.send(content=message_data["content"], embeds=message_data["embeds"], view=view)
            
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


async def setup(bot):
    await bot.add_cog(Moderation(bot))