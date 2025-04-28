import discord 
from discord import app_commands
from discord.ext import commands 
from utilities import colors
from errors.error_logger import error_send
from utilities import send_log, get_all_variables
from utilities import load_roles_ids


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.age_roles_ids = []
        

import discord 
from discord import app_commands
from discord.ext import commands 
from utilities import colors
from errors.error_logger import error_send
from utilities import send_log, get_all_variables
from utilities import load_roles_ids


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.age_roles_ids = []
        

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Load roles
        self.age_roles_ids = load_roles_ids("age", after.guild.id)
        self.gender_roles = load_roles_ids("gender_roles", after.guild.id)
    
        new_roles = [role for role in after.roles if role not in before.roles]
        if not new_roles:
            return
    
        # Check audit log to see WHO made the change
        try:
            entry = None
            async for log in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if log.target.id == after.id and (discord.utils.utcnow() - log.created_at).total_seconds() < 5:
                    entry = log
                    break
        except Exception as e:
            print(f"Error fetching audit log: {e}")
            return
    
        if entry:
            if entry.user.bot or entry.user.guild_permissions.administrator:
                # If a bot or admin did it, ignore
                return
    
        # Normal checks here
        old_age_role = next((r for r in before.roles if r.id in self.age_roles_ids.values()), None)
        old_gender_role = next((r for r in before.roles if r.id in self.gender_roles.values()), None)
    
        for role in new_roles:
            if role.id in self.age_roles_ids.values():
                if old_age_role:
                    try:
                        await after.remove_roles(role, reason="Tried to change age role without permission.")
                        if old_age_role not in after.roles:
                            await after.add_roles(old_age_role, reason="Restoring original age role.")
                    except Exception as e:
                        print(f"Error fixing age role: {e}")
    
            if role.id in self.gender_roles.values():
                if old_gender_role:
                    try:
                        await after.remove_roles(role, reason="Tried to change gender role without verification.")
                        if old_gender_role not in after.roles:
                            await after.add_roles(old_gender_role, reason="Restoring original gender role.")
                    except Exception as e:
                        print(f"Error fixing gender role: {e}")    
async def setup(bot):
    await bot.add_cog(AutoMod(bot))