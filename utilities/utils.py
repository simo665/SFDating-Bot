import discord

async def send_message(interaction, content=None, embed=None, ephemeral=True):
    """Send a message, handling slash command responses or regular interactions."""
    if isinstance(interaction, discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
        else:
            await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
    else:
        await interaction.send(content=content, embed=embed)