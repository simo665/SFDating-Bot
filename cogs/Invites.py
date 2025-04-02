import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from errors.error_logger import error_send

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener()
    async def on_ready(self): 
        for guild in self.bot.guilds:
            self.invites[guild.id] = await guild.invites()
 
    def find_invite_by_code(self, invite_list, code):
        for inv in invite_list:     
            if inv.code == code:      
                return inv
                
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            now = datetime.utcnow()
            three_months_ago = now - timedelta(days=60)
            if not member.created_at.replace(tzinfo=None) <= three_months_ago:
                return 
                    
            invites_before_join = self.invites[member.guild.id]
            invites_after_join = await member.guild.invites()
            for invite in invites_before_join: 
                if invite.uses < self.find_invite_by_code(invites_after_join, invite.code).uses:
                    inviter = invite.inviter
                    inviter_member = member.guild.get_member(inviter.id)  # Get the Member object
                    if inviter_member and inviter_member != member:  # Check if inviter is a member of the guild
                        role = discord.utils.get(member.guild.roles, id=1354089800944058500)
                        if role:
                            await inviter_member.add_roles(role, reason="Invited a member!")
                    self.invites[member.guild.id] = invites_after_join
                    return
        except Exception:
            await error_send()


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))