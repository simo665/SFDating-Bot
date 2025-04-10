import discord
import asyncio
from utilities import colors
import sqlite3 
from errors.error_logger import error_send

gender_roles_ids = {
    "male": 1350851135501766746,
    "female": 1350851138139852810,
    "transmale": 1359888608508510430,
    "transfemale": 1359888703211704431,
    "none": 1359888867750318160
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

async def gender_roles(interaction, values):
    user = interaction.user
    guild = interaction.guild
    try:
        value = values[0]
        female = discord.utils.get(guild.roles, id=gender_roles_ids["female"])
        male = discord.utils.get(guild.roles, id=gender_roles_ids["male"])
        tm = discord.utils.get(guild.roles, id=gender_roles_ids["transmale"])
        tf = discord.utils.get(guild.roles, id=gender_roles_ids["transfemale"])
        none = discord.utils.get(guild.roles, id=gender_roles_ids["none"])
        g_list = [female, male, tm, tf, none]
        
        if not all(g_list):
            embed1 = discord.Embed(title="", color=colors.forbidden)
            embed1.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport2.png")
            embed2 = discord.Embed(title="Oops", description="Technical issues, will be fixed soon 🙏\nReport it in https://discord.com/channels/1349136661971206268/1349244644247998516", color=colors.forbidden)
            await send(interaction, embed=[embed1, embed2])
            return
        
        if any(role in user.roles for role in g_list):
            embed1 = discord.Embed(title="", color=colors.forbidden)
            embed1.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport2.png")
            embed2 = discord.Embed(title="Unauthorized", description="You already have a gender role assigned. If you selected it by mistake, you'll need to verify yourself first to prevent catfishing.\n\n**[Click To Verify](https://discord.com/channels/1349136661971206268/1349244585947299921)**.", color=colors.forbidden)
            await send(interaction, embed=[embed1, embed2])
            return 
        
        chosen_role = discord.utils.get(guild.roles, id=gender_roles_ids[value])
        await user.add_roles(chosen_role, reason="Self roles")
        embed = discord.Embed(title="Gender role assigned!", description=f"✅ You have claimed {chosen_role.mention} role!", color=colors.primary)
        await send(interaction, embed=embed)
        return 
    except Exception:
        await error_send(interaction)
    
    
    