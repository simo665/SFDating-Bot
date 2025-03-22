import discord


def get_member_variables(member):
    return {
        "membermention": member.mention,
        "memberid": str(member.id),
        "memberdisplayname": member.display_name,
        "memberuser": member.name,
        "memberavatarurl": member.display_avatar.url,
        "membercreatedat": member.created_at.isoformat() if member.created_at else None,
        "memberjoinedat": member.joined_at.isoformat() if member.joined_at else None,
        "memberroles": [role.name for role in member.roles if role.name != "@everyone"],
        "membertoprole": member.top_role.name if member.top_role else None,
        "memberstatus": str(member.status),
    }


def get_server_variables(guild):
    return {
        "servername": guild.name,
        "serverid": str(guild.id),
        "serverownermention": guild.owner.mention if guild.owner else None,
        "serverownerid": str(guild.owner_id),
        "servermembercount": guild.member_count,
        "servercreatedat": guild.created_at.isoformat(),
        "servericonurl": guild.icon.url if guild.icon else None,
        "serverbannerurl": guild.banner.url if guild.banner else None,
        "serverboostcount": guild.premium_subscription_count,
        "serverboosttier": guild.premium_tier,
        "serverdescription": guild.description,
    }


def get_moderator_variables(moderator):
    return {
        "modmention": moderator.mention,
        "modid": str(moderator.id),
        "moddisplayname": moderator.display_name,
        "moduser": moderator.name,
        "modavatarurl": moderator.display_avatar.url,
        "modtoprole": moderator.top_role.name if moderator.top_role else None,
    }

def get_emojis_variables():
    return {
        "emoji_timeout": "<:timeout:1352033199408025700>",
        "emoji_unmute": "<:unmute:1352034939037814916>",
        "emoji_ban": "<:ban:1352034994779852981>",
        "emoji_unban": "<:unban:1352035012798840924>",
        "emoji_warn": '<:warn:1352035027772375141>',
        "emoji_memberleft": "<:memberleft:1352035057442750555>",
        "emoji_memberjoined": "<:memberjoined:1352035070030118949>",
        "emoji_member": "<:members:1352035082579214417>",
        "emoji_created": "<:created:1352035097821577246>",
        "emoji_kicked": "<:kicked:1352035111331172493>",
        "emoji_responsible": "<:responsible:1352035129375199252>",
        "emoji_channel": "<:channel:1352035143363330048>",
        "emoji_forbidden": "<:forbidden:1352035161444847686>",
        "emoji_trash": "<:trash:1352035188422475788>",
        "emoji_skull": "<:skull:1352037906075750491>",
        "emoji_reason": "<:reason:1352038968408936520>",
        "emoji_id": "<:id:1352039032934367243>",
        "emoji_offender": "<:offender:1352040640535597056>"
    }

def get_all_variables(member, guild, moderator):
    variables = {}
    variables.update(get_member_variables(member))
    variables.update(get_server_variables(guild))
    variables.update(get_moderator_variables(moderator))
    variables.update(get_emojis_variables())
    return variables