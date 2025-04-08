import discord
from utilities import colors
from errors.error_logger import error_send
from utilities.roles_change import replace_roles

roles_ids = {
    "gamer": 1350851095173271593,
    "music": 1350851096746397737,
    "book": 1350851097828261940,
    "cooking": 1350851100797964288,
    "movie": 1350851099510313030,
    "fitness": 1350851102152589365,
    "anime": 1350851103876710513,
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

async def hobbies_roles(interaction, values):
    user = interaction.user
    guild = interaction.guild
    try:
        added_roles, removed_roles = await replace_roles(user, guild, values, roles_ids)
        embed = discord.Embed(title="Hobbies roles!", description=f"The following roles has been added successfully:\n{'\n'.join(added_roles)}"+(f"\nRemoved roles:\n{'\n'.join(removed_roles)}" if removed_roles else ""), color=colors.primary)
        await send(interaction, embed=embed)
    except Exception:
        await error_send(interaction)