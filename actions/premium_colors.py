import discord
from utilities import colors
from errors.error_logger import error_send
from utilities.roles_change import replace_roles


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

async def premium_colors(interaction, values):
    from utilities import load_roles_ids
    user = interaction.user
    guild = interaction.guild
    roles_ids = load_roles_ids("colors_premium", guild.id)
    premium_role_id = load_roles_ids("premium_role", guild.id)
    try:
        premium_role = discord.utils.get(guild.roles, id=premium_role_id)
        if premium_role not in user.roles:
            embed1 = discord.Embed(title="", color=colors.error)
            embed1.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport2.png")
            embed2 = discord.Embed(title="Missing Premium", description="These colors are for premium members only. please join the premium membership first.\n\n-> **[Premium Info](https://discord.com/channels/1349136661971206268/1350270161000599612)**", color=colors.error)
            await send(interaction, embed=[embed1, embed2])
            return 
        added_roles, removed_roles = await replace_roles(user, guild, values, roles_ids)
        embed = discord.Embed(title="Color Roles!", description=f"The following roles has been added successfully:\n{'\n'.join(added_roles)}"+(f"\nRemoved roles:\n{'\n'.join(removed_roles)}" if removed_roles else ""), color=colors.primary)
        await send(interaction, embed=embed)
    except Exception:
        await error_send(interaction)