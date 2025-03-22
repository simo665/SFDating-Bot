import discord 
from typing import List
from utilities.utils import send_message
from utilities import colors
import random



class Permissions:
    def __init__(self, interaction):
        self.interaction = interaction
        self.messages = {
            "self_moderation_messages": [
                "Oops, can't moderate yourself, try again!",
                "Haha, even superheroes need sidekicks!",
                "You can't be the judge and the defendant!",
                "No self-moderation allowed, nice try!",
                "Trying to ban yourself? Not happening!"
            ],
            "bot_moderation_messages": [
                "You can't moderate me, I'm the bot! 😎",
                "Not today, I’m untouchable!",
                "Nice try, but I’m off-limits!",
                "I’m the bot, I can’t be moderated!",
                "No bot-banning allowed here!"
            ],
            "owner_moderation_messages": [
                "You can’t touch the owner, they're the boss!",
                "Nice try, but the owner’s safe!",
                "The owner? Not even you can touch them!",
                "Sorry, the owner’s off-limits!",
                "I don't think the owner would appreciate that!"
            ],
            "higher_moderator_messages": [
                "You can’t moderate higher-ups, they’re the big guns!",
                "The higher-ups have spoken, no moderation allowed!",
                "Nice try, but you can’t ban your superiors!",
                "Sorry, only moderators can take on higher mods!",
                "You’re not authorized to moderate someone higher than you!"
            ],
            "bot_role_higher_messages": [
                "I can’t moderate members with a higher role than me!",
                "Can’t ban someone with a role higher than mine!",
                "I can’t touch someone more powerful than me!",
                "Sorry, I can't do that, they're too high-ranking for me!",
                "Nope, I’m not powerful enough to moderate them!"
            ]
        }
    
    async def check_guild_permission(self, member: discord.Member, permissions: List):
        for perm in permissions:
            if not getattr(member.guild_permissions, perm, False):
                response_embed = discord.Embed(title="Lack Of Permission", color=colors.forbidden)
                response_embed.description = f"Awh! I don't have `{perm}` permissions." if member.bot else f"Oop! You don't have {perm} permission, lol."
                await send_message(self.interaction, embed=response_embed)
                return False
        return True
    
    async def check_channel_permission(self, member: discord.Member, channel: discord.TextChannel, permissions: List):
        member_permissions = channel.permissions_for(member) 
        for perm in permissions:
            if not getattr(member_permissions, perm, False):
                response_embed = discord.Embed(title="Lack Of Permission", color=colors.forbidden)
                response_embed.description = f"Awh! I don't have `{perm}` permissions in {channel.mention} channel." if member.bot else f"Oop! You don't have {perm} permission in {channel.mention} channel, lol."
                await send_message(self.interaction, embed=response_embed)
                return False
        return True
    
    async def check_mod_rules(self, target_member: discord.Member):
        # Get the command author (user who invoked the command)
        cmd_author = self.interaction.user if isinstance(self.interaction, discord.Interaction) else self.interaction.author
        bot = self.interaction.guild.me  # The bot itself
        owner = self.interaction.guild.owner  # The guild owner
        
        # prepare response embed
        response_embed = discord.Embed(title="Against Moderation Rules!", description="", color=colors.forbidden)
        
        # 1. Self-moderation check: Command author cannot moderate themselves
        if cmd_author.id == target_member.id:
            response_embed.description = random.choice(self.messages["self_moderation_messages"])
            await send_message(self.interaction, embed=response_embed)
            return False
    
        # 2. Moderation against the bot: Command author cannot moderate the bot
        if target_member.id == bot.id:
            response_embed.description = random.choice(self.messages["bot_moderation_messages"])
            await send_message(self.interaction, embed=response_embed)
            return False
    
        # 3. Moderation against the owner: Command author cannot moderate the guild owner
        if target_member.id == owner.id:
            response_embed.description = random.choice(self.messages["owner_moderation_messages"])
            await send_message(self.interaction, embed=response_embed)
            return False
    
        # 4. Moderation against a higher moderator:
        # If the target member has a higher role than the command author AND has the 'moderate_members' permission,
        # the command author cannot moderate them.
        if target_member.top_role > cmd_author.top_role and target_member.guild_permissions.moderate_members:
            response_embed.description = random.choice(self.messages["higher_moderator_messages"])
            await send_message(self.interaction, embed=response_embed)
            return False
    
        # 5. Target member higher than the bot: Bot cannot moderate members with a higher role
        if target_member.top_role > bot.top_role:
            response_embed.description = random.choice(self.messages["bot_role_higher_messages"])
            await send_message(self.interaction, embed=response_embed)
            return False
    
        # If none of the above conditions are met, moderation is allowed
        return True