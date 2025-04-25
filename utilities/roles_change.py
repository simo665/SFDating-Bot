import discord 
from utilities import colors
from utilities.utils import send_message

async def replace_roles(user, guild, values, roles_dict, interaction=None):
    # remove previous roles
    removed_roles = []
    roles_to_remove = []
    for role in user.roles:
        if role.id in roles_dict.values():
            roles_to_remove.append(role)
            removed_roles.append(f"❌ {role.mention} removed!")
    
    await user.remove_roles(*roles_to_remove, reason="Self Roles assignment.")
    
    # add new roles:
    added_roles = []
    roles_to_add = []
    for value in values:
        selected_role = discord.utils.get(guild.roles, id=roles_dict[value])
        if not selected_role:
            embed1 = discord.Embed(title="", color=colors.error)
            embed1.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport2.png")
            embed2 = discord.Embed(title="Oops", description="Technical issues, will be fixed soon!", color=colors.error)
            if interaction:
                await send_message(interaction, embed=[embed1, embed2])
            continue 
        roles_to_add.append(selected_role)
        added_roles.append(f"✅ {selected_role.mention} added!")
        removed_format = f"❌ {selected_role.mention} removed!" 
        if removed_format in removed_roles:
            removed_roles.remove(removed_format)
    
    await user.add_roles(*roles_to_add, reason="Self roles assignment.")
    
    return added_roles, removed_roles