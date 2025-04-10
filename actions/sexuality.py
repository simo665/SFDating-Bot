import discord
import asyncio
from utilities import colors
import sqlite3 
from errors.error_logger import error_send
from utilities.roles_change import replace_roles

roles_ids = {
    "straight": 1359787396753002616,
    "gay": 1359788005048455188,
    "bisexual": 1359787539304808550,
    "lesbian": 1359787883887726622,
    "pansexual": 1359788104407322718,
    "asexual": 1359788670650945628,
    "demisexual": 1359788893494317187,
    "queer": 1359789167210397699,
    "none": 1359789289176698890,
}
 
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


    

async def sexuality(interaction, values):
    user = interaction.user
    guild = interaction.guild
    try:
        added_roles, removed_roles = await replace_roles(user, guild, values, roles_ids)
        embed = discord.Embed(title="Sexuality roles!", description=f"The following roles has been added successfully:\n{'\n'.join(added_roles)}"+(f"\nRemoved roles:\n{'\n'.join(removed_roles)}" if removed_roles else ""), color=colors.primary)
        await send(interaction, embed=embed)
    except Exception:
        await error_send(interaction)