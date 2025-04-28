import discord
import logging

logger = logging.getLogger('bot.shop_paginator')

class ShopPaginator(discord.ui.View):
    """A pagination view for shop embeds"""
    
    def __init__(self, embeds):
        super().__init__(timeout=120)  # Buttons auto-disable after 2 minutes
        self.embeds = embeds
        self.current_page = 0
        self.message = None
        
    async def update_message(self, interaction: discord.Interaction):
        """Update the embed when the user clicks a button"""
        try:
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        except Exception as e:
            logger.error(f"Error updating message: {e}")

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.blurple)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the previous page"""
        if interaction.user != self.message.interaction_metadata.user:
            await interaction.response.send_message("You cannot use these controls.", ephemeral=True)
            return
            
        self.current_page = max(0, self.current_page - 1)
        await self.update_message(interaction)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the next page"""
        if interaction.user != self.message.interaction_metadata.user:
            await interaction.response.send_message("You cannot use these controls.", ephemeral=True)
            return
            
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        await self.update_message(interaction)

    async def on_timeout(self):
        """Disable buttons after timeout to prevent spam"""
        for item in self.children:
            item.disabled = True
            
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception as e:
                logger.error(f"Error disabling buttons: {e}")