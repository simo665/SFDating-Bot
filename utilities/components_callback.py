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
        self.select_callbacks = {
            "ageroles": ageroles,
            "gender": gender_roles,
            "occupation": occupation_roles,
            "relationship_status": relationship_status_roles,
            "dms_status": dms_status_roles,
            "Age preference": age_prefer_status_roles,
            "Region": region_roles,
            "Height Preference": height_preference,
            "distance": distance_preference,
            "personality": personality_roles,
            "partner personality": partner_personality_roles,
            "hobbies": hobbies_roles,
            "colors": colors_roles,
            "basic colors": basic_colors,
            "boosters colors": boosters_colors,
            "premium colors": premium_colors,
            "height": height 
        }

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            if self.custom_id in self.select_callbacks:
                await self.select_callbacks[self.custom_id](interaction, self.values)
        except Exception:
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