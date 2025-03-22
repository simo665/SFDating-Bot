import discord 
from errors.error_logger import error_send
from actions import *

class DropDownSelect(discord.ui.Select):
    def __init__(self, options, custom_id, placeholder, min_values=1, max_values=1):
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            id = self.custom_id
            if id == "ageroles":
                await interaction.response.defer()
                await ageroles(interaction, self.values)
            else:
                await interaction.response.send_message("No response", ephemeral=True)
        except Exception as e:
            await error_send(interaction)

class CustomButton(discord.ui.Button):
    def __init__(self, custom_id, label, style, emoji=None, url=None):
        super().__init__(
            custom_id=custom_id,
            label=label,
            style=discord.ButtonStyle(style),
            emoji=emoji,
            url=url
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"You clicked: {self.label} (ID: {self.custom_id})", 
            ephemeral=True
        )