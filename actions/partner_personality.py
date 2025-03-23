import discord
import asyncio
from utilities import colors
import sqlite3 
from errors.error_logger import error_send
from utilities.roles_change import replace_roles

roles_ids = {
    "introvert partner": 1350851082862989463,
    "extrovert partner": 1350851086008975422,
    "optimistic partner": 1350987464960905226,
    "ambivert partner": 1350987302930743401,
    "realist partner": 1350987715310518423,
    "intellectual partner": 1350851089003450453,
    "goofy partner": 1350851091633274921,
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

async def partner_personality_roles(interaction, values):
    user = interaction.user
    guild = interaction.guild
    try:
        added_roles, removed_roles = await replace_roles(user, guild, values, roles_ids)
        embed = discord.Embed(title="Partner Personality roles!", description=f"The following roles has been added successfully:\n{'\n'.join(added_roles)}"+(f"\nRemoved roles:\n{'\n'.join(removed_roles)}" if removed_roles else ""), color=colors.primary)
        await send(interaction, embed=embed)
    except Exception:
        await error_send(interaction)