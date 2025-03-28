import discord 
from discord import app_commands
from discord.ext import commands 
from utilities import Permissions, colors, get_all_variables
from utilities import send_log, send_notif, get_link, format_time
import asyncio
from errors.error_logger import error_send
from typing import List
import sqlite3 
import datetime
import time




class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.delete_delay = 5
        self.conn = sqlite3.connect("database/data.db")
        self.create_table()
        
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
    
    def upsert_config(self, guild_id: int, column: str, value: int):
        cur = self.conn.cursor()
        try:
            cur.execute(f"SELECT 1 FROM configs WHERE guild_id = ?", (guild_id,))
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
    @app_commands.describe(role="Jail role. If you don't have one do '/jail create'")
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
            authorized = await self.check_perm(interaction, ["administrator"], ["mmanage_roles"])
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
                response_embed.description = f"I don't have permission to create roles. make sure to give me manage roles permission."
                await original_response.edit(embed=response_embed)
                return 
            # Get bot top role position 
            highest_role = max((role for role in guild.roles if role < guild.me.top_role), key=lambda r: r.position)
            # move role right below the bot highest role 
            if highest_role:
                await role.edit(position=highest_role.position)
            # loop through all channels and add permissions restrictions for the role 
            for channel in guild.channels:
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
    async def jail(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment = None):
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
        except Exception as e:
            await error_send(interaction)
    
    @jail_group.command(name="remove", description="Unjail a user.")
    @app_commands.describe(member="Target member.", reason="Why are they getting Unjailed? did they verify themselves?", proof="Do you have a proof you want to provide?")
    async def unjail(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment = None):
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
        except Exception as e:
            await error_send(interaction)

    #  _______________________ Sus Commands  _______________________ 
    sus_group = app_commands.Group(name="sus", description="Sus related commands")
    @sus_group.command(name="setup", description="Add suspicious role to a specific member.")
    async def sus_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            authorized = await self.check_perm(interaction, ["administrator"], ["manage_roles"])
            if not authorized:
                return 
            # set up the role
            guild = interaction.guild
            role = None
            cur = self.conn.cursor()
            try: 
                cur.execute("SELECT sus_role_id FROM configs WHERE guild_id = ?", (guild.id,))
                result = cur.fetchone()
                self.conn.commit()
                role = discord.utils.get(result[0]) if result else None
                if not role:
                    role = await guild.create_role(name="Sus", color=0xfa0606)
                    self.upsert_config(guild.id, "sus_role_id", role.id)
            except discord.Forbidden:
                response_embed.description = f"I don't have permission to create roles. make sure to give me manage roles permission."
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

1. Go to each channel where you **don’t** want suspicious users to have access.  
2. **Hold-click** on the channel → **Edit Channel** → **Permissions**.  
3. Click **Add Role** and select {role.mention}.  
4. Under **Permissions**, disable the following:  
   - **View Channels** = ❌  
   - **Send Messages** = ❌  
5. (Optional) Adjust other permissions as needed. If you want to **completely hide** the channel from them, ensure both settings above are disabled.  

That's it! Now, suspicious users won’t be able to see or interact in those channels.
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
    async def sus(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment = None):
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
        except Exception as e:
            await error_send(interaction)
    
    @sus_group.command(name="remove", description="Remove suspicious role from a specific member.")
    @app_commands.describe(member="Target member.", reason="Why are they getting unsus? did they verify?", proof="Do you have a proof against them?")
    async def unsus(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment = None):
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
        except Exception as e:
            await error_send(interaction)
    
    
    #  _______________________ Warn Commands  _______________________
    warn_group = app_commands.Group(name="warn", description="Warn/Unwarn a member with timeout if needed.")
    @warn_group.command(name="add", description="Add a warning to a member.")
    @app_commands.choices(timeout=[
        app_commands.Choice(name="No timeout needed.", value=300),
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
    async def warn(self, interaction: discord.Interaction, member: discord.Member, timeout: app_commands.Choice[int], reason: str, proof: discord.Attachment = None):
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
            await response.delete()
        except Exception as e:
            await error_send(interaction)
    
    @warn_group.command(name="remove", description="Remove a warning from a member.")
    async def unwarn(self, interaction: discord.Interaction, member: discord.Member, reason: str, proof: discord.Attachment = None):
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
            await response.delete()
        except Exception as e:
            await error_send(interaction)

    #  _______________________ Verification Commands  _______________________
    verify = app_commands.Group(name="verify", description="Verification commands.")
    @verify.command(name="add", description="Verify a member.")
    @app_commands.choices(
        gender = [
            app_commands.Choice(name="♀️ Female", value="female"),
            app_commands.Choice(name="♂️ Male", value="male")
        ]
    )
    @app_commands.choices(
        age = [
            app_commands.Choice(name="18 years old", value=18),
            app_commands.Choice(name="19 years old", value=19),
            app_commands.Choice(name="20 years old", value=20),
            app_commands.Choice(name="21 years old", value=21),
            app_commands.Choice(name="22 years old", value=22),
            app_commands.Choice(name="23 years old", value=23),
            app_commands.Choice(name="24 years old", value=24),
            app_commands.Choice(name="25+ years old", value=25)
        ]
    )
    @app_commands.describe(member="Who is the member you are trying to verify?", gender="What is their gender?", age="What is their age?", proof="Show a proof of their verification (e.g screenshot)")
    async def verify_cmd(self, interaction: discord.Interaction, member: discord.Member, gender: app_commands.Choice[str], age: app_commands.Choice[int], proof: discord.Attachment):
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
            gender_roles_ids = {
                "male": 1350851135501766746,
                "female": 1350851138139852810,
            }
            age_roles_ids = {
                18: 1350851110021238795,
                19: 1350851112437026876,
                20: 1350851115096473651,
                21: 1350851117000425562,
                22: 1350851119215280139,
                23: 1350851123531218965,
                24: 1350851127897358410,
                25: 1350851131961511957
            }
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
            
            verified_roles = {
                "male": 1350898361032642641, # verified Male 
                "female": 1350898277813583932 # verified Female 
            }
            
            verified_role = discord.utils.get(guild.roles, id=verified_roles[gender.value])
            
            if not verified_role:
                embed = discord.Embed(title="<:forbidden:1352035161444847686> Error", description=f"verified {gender.value} role is not found! member can't be verified.\nReport this to Simo.", color=colors.error)
                if issues:
                    embed.add_feild(name="<:warn:1352035027772375141> Other issues:", value="\n".join(issues))
                await interaction.followup.send(embed=embed, ephemeral=True)
                return 
            
            # Check in case the user have already the opposite gender verification role
            for role in member.roles:
                if role.id in verified_roles.values() and role.id != verified_role.id:
                    await member.remove_roles(role, reason="Remove previous verification roles. prolly assigned by mistake.")
             
            await member.add_roles(verified_role, reason="Verified member role added!")
            
            # Remove jail/sus roles if exists 
            sus_role = discord.utils.get(guild.roles, id=1350895174124961909)
            jail_role = discord.utils.get(guild.roles, id=1350169044191285348)
            # get variables 
            variables = get_all_variables(member, guild, interaction.user)
            
            if sus_role in member.roles:
                await send_notif(member, variables, "notif_unsus")
            if jail_role in member.roles:
                await send_notif(member, variables, "notif_unjail")
                
            await member.remove_roles(sus_role, jail_role, reason="Remove previous verification roles. prolly assigned by mistake.")
            # response 
            embed = discord.Embed(title="<a:TwoHearts:1353727250394124328> Verified Successfully!", description=f"<a:Heartribbon:1353727310276198494> {member.mention} Was verified successfully!", color=colors.primary)
            if issues:
                embed.add_feild(name="<:warn:1352035027772375141> Other issues:", value="\n".join(issues))
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # logs and notification 
            proof_url = None
            if proof:
                proof_url = await get_link(proof)
            variables.update({"proofurl": proof_url if proof_url else ""})
            # send log
            await send_log(self.bot, variables, "log_verified")
            await send_notif(member, variables, "notif_verified")
        except Exception as e:
            await error_send(interaction)
    


async def setup(bot):
    await bot.add_cog(Moderation(bot))