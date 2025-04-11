import discord
from utilities import colors
import sqlite3 
from errors.error_logger import error_send

age_roles_ids = {
    "age18": 1350851110021238795,
    "age19": 1350851112437026876,
    "age20": 1350851115096473651,
    "age21": 1350851117000425562,
    "age22": 1350851119215280139,
    "age23": 1350851123531218965,
    "age24": 1350851127897358410,
    "age25": 1350851131961511957
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

async def ageroles(interaction, values):
    from utilities.variables import get_all_variables
    from utilities.user_notif import send_notif
    from utilities.logging_handler import send_log
    user = interaction.user
    try:
        value = values[0]
        if value == "underage" or value == "overage":
            con = sqlite3.connect("database/data.db")
            jail_role_id = None
            cur = con.cursor()
            try:
                cur.execute("SELECT jail_role_id FROM configs WHERE guild_id = ?", (interaction.guild.id,))
                result = cur.fetchone()
                con.commit()
                jail_role_id = result[0] if result else None
            finally:
                cur.close()
            if jail_role_id and discord.utils.get(interaction.guild.roles, id=jail_role_id):
                await user.add_roles(discord.utils.get(interaction.guild.roles, id=jail_role_id), reason=value)
                variables = get_all_variables(user, interaction.guild, interaction.user)
                variables.update({'reason': value, 'proofurl': ""})
                await send_notif(user, variables, "notif_jail")
                await send_log(interaction.client, variables, "log_jail")
            else:
                await user.ban(reason=value)
            return 
        
        for role in user.roles:
            if role.id in age_roles_ids.values():
                embed1 = discord.Embed(title="", color=colors.forbidden)
                embed1.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport2.png")
                embed2 = discord.Embed(title="Unauthorized", description="You already have an age role assigned. If you selected it by mistake or need to update it, you'll need to verify your age first to prevent misuse.\n\n**[Click To Verify](https://discord.com/channels/1349136661971206268/1349244585947299921)**.", color=colors.forbidden)
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
    
    
    