import discord
import asyncio
from utilities import colors
import sqlite3 
from errors.error_logger import error_send
from utilities.roles_change import replace_roles

roles_ids = {
    "introvert": 1353392254043033651,
    "extrovert": 1353392255309713499,
    "optimist": 1353392259386708020,
    "ambivert": 1353392257465712724,
    "realistic": 1353392260619960371,
    "intellectual": 1353392256459210902,
    "goofy": 1353392261521739849,
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

async def personality_roles(interaction, values):
    user = interaction.user
    guild = interaction.guild
    try:
        added_roles, removed_roles = await replace_roles(user, guild, values, roles_ids)
        embed = discord.Embed(title="Personality roles!", description=f"The following roles has been added successfully:\n{'\n'.join(added_roles)}"+(f"\nRemoved roles:\n{'\n'.join(removed_roles)}" if removed_roles else ""), color=colors.primary)
        await send(interaction, embed=embed)
    except Exception:
        await error_send(interaction)