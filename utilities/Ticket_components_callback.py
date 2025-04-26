import discord
from typing import List, Optional, Union

class CustomButton(discord.ui.Button):
    """Custom button implementation for the ticket system"""
    def __init__(
        self, 
        custom_id: str = None, 
        label: str = None,
        style: int = discord.ButtonStyle.primary, 
        emoji: Union[str, discord.Emoji, discord.PartialEmoji] = None,
        url: str = None, 
        disabled: bool = False,
        row: Optional[int] = None
    ):
        # Convert integer style to discord.ButtonStyle if needed
        if isinstance(style, int):
            button_styles = {
                1: discord.ButtonStyle.primary,
                2: discord.ButtonStyle.secondary,
                3: discord.ButtonStyle.success,
                4: discord.ButtonStyle.danger,
                5: discord.ButtonStyle.link
            }
            style = button_styles.get(style, discord.ButtonStyle.primary)
        
        super().__init__(
            style=style,
            custom_id=custom_id,
            label=label,
            emoji=emoji,
            url=url,
            disabled=disabled,
            row=row
        )
    
    async def callback(self, interaction: discord.Interaction):
        # This will be overridden by the actual callback implementation
        await interaction.response.defer()


class DropDownSelect(discord.ui.Select):
    """Custom select menu implementation for the ticket system"""
    def __init__(
        self,
        options: List[discord.SelectOption],
        custom_id: str = None,
        placeholder: str = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        row: Optional[int] = None
    ):
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
            row=row
        )

    async def callback(self, interaction: discord.Interaction):
        # This will be overridden by the actual callback implementation
        await interaction.response.defer()
