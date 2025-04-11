import discord
from utilities import colors
from errors.error_logger import error_send
from utilities.roles_change import replace_roles

roles_ids = {
    "48": 1353905823381848115,
    "50": 1353905959491338333,
    "52": 1353906092668747857,
    "54": 1353906187686383636,
    "56": 1353906287871656007,
    "58": 1353906388463521832,
    "60": 1353906493266854018,
    "62": 1353906593175179295,
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


async def height(interaction, values):
    user = interaction.user
    guild = interaction.guild
    try:
        added_roles, removed_roles = await replace_roles(user, guild, values, roles_ids)
        embed = discord.Embed(title="Height roles!", description=f"The following roles has been added successfully:\n{'\n'.join(added_roles)}"+(f"\nRemoved roles:\n{'\n'.join(removed_roles)}" if removed_roles else ""), color=colors.primary)
        await send(interaction, embed=embed)
    except Exception:
        await error_send(interaction)