import discord
from utilities import colors
import sqlite3 
from errors.error_logger import error_send
from dotenv import load_dotenv
import os

load_dotenv()
verification_channel = os.getenv("VERIFICATION_CHANNEL")


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

async def ageroles(interaction, values):
    from utilities.variables import get_all_variables
    from utilities.user_notif import send_notif
    from utilities.logging_handler import send_log
    from utilities import load_roles_ids
    age_roles_ids = load_roles_ids("age", interaction.guild.id)
    user = interaction.user
    try:
        value = values[0]
    
        for role in user.roles:
            if role.id in age_roles_ids.values():
                embed1 = discord.Embed(title="", color=colors.forbidden)
                embed1.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport2.png")
                embed2 = discord.Embed(title="Unauthorized", description=f"You already have an age role assigned. If you selected it by mistake or need to update it, you'll need to verify your age first to prevent misuse.\n\n**[Click To Verify]({verification_channel})**.", color=colors.forbidden)
                await send(interaction, embed=[embed1, embed2])
                return 
            
        selected_age = age_roles_ids[value]
        age_role = discord.utils.get(interaction.guild.roles, id=selected_age)
        if not age_role:
            embed1 = discord.Embed(title="", color=colors.error)
            embed1.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport2.png")
            embed2 = discord.Embed(title="Opps", description="Technical issues, will be fixed soon!", color=colors.error)
            await send(interaction, embed=[embed1, embed2])
            return 
        await user.add_roles(age_role, reason="Self-roles assigned.")
        embed = discord.Embed(title="Age role assigned!", description=f"✅ You have claimed {age_role.mention} role!", color=colors.primary)
        await send(interaction, embed=embed)
        return 
    except Exception:
        await error_send(interaction)
    
    
    