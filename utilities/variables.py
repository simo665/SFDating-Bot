import discord


def get_member_variables(member):
    return {
        "membermention": member.mention if member else "/",
        "memberid": str(member.id) if member else "/",
        "memberdisplayname": member.display_name if member else "/",
        "memberuser": member.name if member else "/",
        "memberavatarurl": member.display_avatar.url if member else "",
        "membercreatedat": (member.created_at.isoformat() if member.created_at else None) if member else "/",
        "memberjoinedat": (member.joined_at.isoformat() if member.joined_at else None) if member else "/",
        "memberroles": ([role.name for role in member.roles if role.name != "@everyone"]) if member else "/",
        "membertoprole": (member.top_role.name if member.top_role else None) if member else "/",
        "memberstatus": str(member.status) if member else "/",
    }


def get_server_variables(guild):
    return {
        "servername": guild.name if guild else "/",
        "serverid": str(guild.id) if guild else "/",
        "serverownermention": (guild.owner.mention if guild.owner else None) if guild else "/",
        "serverownerid": str(guild.owner_id) if guild else "/",
        "servermembercount": guild.member_count if guild else "/",
        "servercreatedat": guild.created_at.isoformat() if guild else "/",
        "servericonurl": (guild.icon.url if guild.icon else None) if guild else "",
        "serverbannerurl": (guild.banner.url if guild.banner else None) if guild else "",
        "serverboostcount": guild.premium_subscription_count if guild else "/",
        "serverboosttier": guild.premium_tier if guild else "/",
        "serverdescription": guild.description if guild else "/",
    }


def get_moderator_variables(moderator):
    return {
        "modmention": moderator.mention if moderator else "/",
        "modid": str(moderator.id) if moderator else "/",
        "moddisplayname": moderator.display_name if moderator else "/",
        "moduser": moderator.name if moderator else "/",
        "modavatarurl": moderator.display_avatar.url if moderator else "",
        "modtoprole": (moderator.top_role.name if moderator.top_role else None) if moderator else "/",
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
        "emoji_offender": "<:offender:1352040640535597056>",
        "redglassheart": "<a:redglassheart:1353727228680212510>",
        "PinkHearts": "<a:PinkHearts:1353727242177478687>",
        "blowingHearts": "<a:blowingHearts:1353727249354064026>",
        "TwoHearts": "<a:TwoHearts:1353727250394124328>",
        "HeartMessage": "<a:HeartMessage:1353727263933464596>",
        "PurpleHearts": "<a:PurpleHearts:1353727264054841386>",
        "HeartPopUp": "<a:HeartPopUp:1353727277099126835>",
        "Heartribbon": "<a:Heartribbon:1353727310276198494>",
        "Heartspin": "<a:Heartspin:1353727321508679692>",
        "FoxHi": "<a:FoxHi:1353732995130851408>",
        "Crown": "<a:Crown:1353865280312578139>"
    }

def get_all_variables(member, guild, moderator):
    variables = {}
    variables.update(get_member_variables(member))
    variables.update(get_server_variables(guild))
    variables.update(get_moderator_variables(moderator))
    variables.update(get_emojis_variables())
    return variables