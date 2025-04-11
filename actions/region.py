import discord
from utilities import colors
from errors.error_logger import error_send
from utilities.roles_change import replace_roles

roles_ids = {
    "north America": 1350851068426190920,
    "south america": 1350851076554883072,
    "europe": 1350851070384934934,
    "asia": 1350851072150999235,
    "africa": 1350851074654998529,
    "australia": 1350851078521880586,
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


async def region_roles(interaction, values):
    user = interaction.user
    guild = interaction.guild
    try:
        added_roles, removed_roles = await replace_roles(user, guild, values, roles_ids)
        embed = discord.Embed(title="Region status roles!", description=f"The following roles has been added successfully:\n{'\n'.join(added_roles)}"+(f"\nRemoved roles:\n{'\n'.join(removed_roles)}" if removed_roles else ""), color=colors.primary)
        await send(interaction, embed=embed)
    except Exception:
        await error_send(interaction)