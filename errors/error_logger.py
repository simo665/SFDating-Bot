import traceback 
import logging
import discord 
from utilities import colors

# Configure logging
logging.basicConfig(
    filename="errors/errors.log", 
    filemode="a", 
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.ERROR 
)
logger = logging.getLogger(__name__)

async def error_send(interaction, notify_user = True):
    ## Notify user
    try:
        if notify_user:
            error_embed = discord.Embed(title="Error", description=f"Whoopsie! 😳 Something went wrong, try again!" , color=colors.error)
            if isinstance(interaction, discord.Interaction):
                if interaction.response.is_done():
                    await interaction.followup.send(embed = error_embed, ephemeral=True)
                else: 
                    await interaction.response.send_message(embed = error_embed, ephemeral=True)
            else:
                await interaction.send(embed=error_embed)
    except Exception as e:
        traceback.print_exc()
    ## Log error 
    traceback.print_exc()
    logger.error(f"Error: {traceback.format_exc()}\n"+"="*50+"\n")
