import discord
import asyncio
from utilities import colors
import sqlite3 
from errors.error_logger import error_send
from utilities.roles_change import replace_roles

roles_ids = {
    "basic": "selfroles_basic_roles",
    "boosters": "selfroles_boosters_colors",
    "premium": "selfroles_premium_colors",
}
 

async def colors_roles(interaction, values):
    from utilities import get_message_from_template
    user = interaction.user
    guild = interaction.guild
    try:
        message_data = get_message_from_template(roles_ids[values[0]])
        await interaction.followup.send(embeds=message_data["embeds"], view=message_data["view"], ephemeral=True)
    except Exception:
        await error_send(interaction)