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
        "emoji_timeout": "<:mute:1359816429024710697>",
        "emoji_unmute": "<:unmute:1359816405746323538>",
        "emoji_ban": "<:ban:1359816445596274821>",
        "emoji_unban": "<:unban:1359816458183377036>",
        "emoji_warn": '<:warn:1359816466513526885>',
        "emoji_memberleft": "<:mekberleft:1359816477603270877>",
        "emoji_memberjoined": "<:memberjoin:1359816496934817863>",
        "emoji_member": "<:member:1359816515867771012>",
        "emoji_members": "<:members:1359816510805119057>",
        "emoji_created": "<:Crested_at:1359816533005832385>",
        "emoji_kicked": "<:Kick:1359816537107857489>",
        "emoji_responsible": "<:mod:1359820357107974244>",
        "emoji_channel": "<:channel:1359820370017783971>",
        "emoji_forbidden": "<:forbidden:1359820382177198308>",
        "emoji_trash": "<:trash:1359820401621995551>",
        "emoji_skull": "<:skull:1359820404092305490>",
        "emoji_reason": "<:reason:1359820414158635018>",
        "emoji_id": "<:id:1359821324192841828>",
        "emoji_offender": "<:offender:1359822110469390427>",
        "redglassheart": "<a:redglassheart:1359831104995070183>",
        "PinkHearts": "<a:PinkHearts:1359829058942144594>",
        "blowingHearts": "<a:blowingHearts:1359829944774955058>",
        "TwoHearts": "<a:TwoHearts:1359827390616047726>",
        "HeartMessage": "<a:HeartMessage:1359827376644821113>",
        "PurpleHearts": "<a:PurpleHearts:1359832278854930482>",
        "HeartPopUp": "<a:HeartPopUp:1359829671503466536>",
        "Heartribbon": "<a:Heartribbon:1359828243947061339>",
        "Heartspin": "<a:Heartspin:1359829315633680497>",
        "CatHeart": "<a:CatHeart:1359823813356818603>",
        "BlackCatHeart": "<a:BlackCatHeart:1359823829509083169>",
        "LikeHeart": "<a:LikeHeart:1359823755307778189>",
        "FoxHi": "<a:FoxHi:1359830431771398154>",
        "Crown": "<a:Crown:1359833023373115514>",
        "level": "<:level:1360397834419175505>",
        "rank": "<:rank:1360397817373261864>",
        "xp": "<:xp:1360397798184452465>",
        "online": "<a:Online:1363514658136522852>",
        "offline": "<:offline:1363514572572594196>",
    }

def get_all_variables(member, guild, moderator):
    variables = {}
    variables.update(get_member_variables(member))
    variables.update(get_server_variables(guild))
    variables.update(get_moderator_variables(moderator))
    variables.update(get_emojis_variables())
    return variables