import discord
from utilities import colors
from errors.error_logger import error_send
from utilities.roles_change import replace_roles

roles_ids = {
    "single": 1351001902107725935,
    "taken": 1351001988644733050,
    "complicated": 1351002210556842014,
    "not looking": 1351002077198815362,
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


    

async def relationship_status_roles(interaction, values):
    user = interaction.user
    guild = interaction.guild
    try:
        added_roles, removed_roles = await replace_roles(user, guild, values, roles_ids)
        embed = discord.Embed(title="Relationship status roles!", description=f"The following roles has been added successfully:\n{'\n'.join(added_roles)}"+(f"\nRemoved roles:\n{'\n'.join(removed_roles)}" if removed_roles else ""), color=colors.primary)
        await send(interaction, embed=embed)
    except Exception:
        await error_send(interaction)