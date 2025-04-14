import discord  
import json    
from datetime import datetime  
import asyncio
from utilities.get_template import get_message_from_template

channel_id = 1349918918231326800

async def send_log(bot, variables, logname, channel: int = None):
    data = get_message_from_template(logname, variables)
    channel = bot.get_channel(channel_id if not channel else channel)
    if not channel:
        print("channel not found")
        return 
    # send log message to the channel
    await channel.send(data["content"], embeds=data["embeds"], view=data["view"])