import discord  
import json    
from datetime import datetime  
import asyncio
import random
from utilities.get_template import get_message_from_template

# Button View
class ServerLinkView(discord.ui.View):
    def __init__(self, guild_name, channel_link):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label=f"Sent from {guild_name}", 
            url=channel_link, 
            style=discord.ButtonStyle.link
        ))

async def send_notif(user, variables, logname):
    # Get the message template data
    data = get_message_from_template(logname, variables)
    
    guild = user.guild
   
    channel_link = f"https://discord.com/channels/{guild.id}"
    view = ServerLinkView(guild.name, channel_link)

    await user.send(
        content=data["content"], 
        embeds=data["embeds"], 
        view=view
    )