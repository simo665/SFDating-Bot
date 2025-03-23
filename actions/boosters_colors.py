import discord
import asyncio
from utilities import colors
import sqlite3 
from errors.error_logger import error_send
from utilities.roles_change import replace_roles

roles_ids = {
    "pink": 1350447292469084231,
    "soft purple": 1350447559751106610,
    "yellow": 1350447796401999892, 
    "orange": 1350447997791506503
}

boosters_role_id = 1353417520664805446
 
async def send(interaction, embed):
    if interaction.response.is_done():
        if isinstance(embed, list):
            await interaction.followup.send(embeds=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        if isinstance(embed, list):
            await interaction.response.send_message(embeds=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def boosters_colors(interaction, values):
    user = interaction.user
    guild = interaction.guild
    boosters_role = discord.utils.get(guild.roles, id=boosters_role_id)
    try:
        if not boosters_role in user.roles:
            embed1 = discord.Embed(title="", color=colors.error)
            embed1.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport2.png")
            embed2 = discord.Embed(title="Missing Boost role", description="These colors are for boosters members only. please boost the server first.\n\n-> **[How do i boost a server?](https://support.discord.com/hc/en-us/articles/360028038352#h_01HGX7DJ331AJ25MPQRD6R83KJ)**", color=colors.error)
            await send(interaction, embed=[embed1, embed2])
            return 
        added_roles, removed_roles = await replace_roles(user, guild, values, roles_ids)
        embed = discord.Embed(title="Color Roles!", description=f"The following roles has been added successfully:\n{'\n'.join(added_roles)}"+(f"\nRemoved roles:\n{'\n'.join(removed_roles)}" if removed_roles else ""), color=colors.primary)
        await send(interaction, embed=embed)
    except Exception:
        await error_send(interaction)