import discord
from discord import app_commands
from discord.ext import commands
import os
import random
import aiohttp
from dotenv import load_dotenv

load_dotenv()


class ActionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tenor_api_key = os.getenv("TENOR_API_KEY")
        self.kill_gifs = [
            "https://media2.giphy.com/media/yy1rPT45jdX1K/giphy.gif?cid=6c09b952twuokj741sldlmwq3o1eelqsjap6ajz0w32vm31s&ep=v1_internal_gif_by_id&rid=giphy.gif",
            "https://media0.giphy.com/media/BTV1vUcOWht2U/giphy.gif?cid=6c09b952tlgqfkxa0ljle3hn0u6hvywns0vr3r51fbqmmrwx&ep=v1_internal_gif_by_id&rid=giphy.gif",
            "https://i.pinimg.com/originals/d3/05/8f/d3058f387b2a9439e59064af996ab52a.gif",
            "https://64.media.tumblr.com/d62f5d73c6e6e0392c44a1a5e1a3be73/58a16372a61552a0-ee/s500x750/b2a9241b69364ad1065e044297db3e49073bc0ac.gif",
            "https://64.media.tumblr.com/5d232d19f1d859279ca3a4330dd42cd4/2287c980a67ffca5-08/s500x750/42e8f6d2dabeb8aff4b5b25f7f94a04f593e8143.gif",
            "https://media.tenor.com/NbBCakbfZnkAAAAM/die-kill.gif",
            "https://i.pinimg.com/originals/f2/77/11/f27711247fc413105afa7f171d947092.gif",
            "https://giffiles.alphacoders.com/148/148539.gif"
        ]
            

    async def fetch_gif(self, action: str):
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "q": f"anime {action}",
                    "key": self.tenor_api_key,
                    "limit": 30,
                    "contentfilter": "medium"
                }
                async with session.get("https://tenor.googleapis.com/v2/search", params=params) as response:
                    data = await response.json()
                    return random.choice(data["results"])["media_formats"]["gif"]["url"]
        except:
            return ""
    
    actions_group = app_commands.Group(name="actions", description="🌸 Interact with others through sweet gestures!")
    @actions_group.command(name="hug", description="🌸 Hug someone with cherry blossom care!")
    async def hug(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("hug")
        if not member:
            embed = discord.Embed(
                description="🌸 Awh, you feel lonely, don't you? Come here... let's hug! 🤗",
                color=0xffb7c5
            )
        else:
            embed = discord.Embed(
                description=f"🌸 **{interaction.user.display_name}** sends a warm sakura hug to **{member.display_name}**!",
                color=0xffb7c5
            )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)

    @actions_group.command(name="kiss", description="🌸 Plant a gentle sakura kiss!")
    async def kiss(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("kiss")
        if not member:
            embed = discord.Embed(
                description="🌸 Blushing~ Are you asking me for a kiss? (⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)💞",
                color=0xff9ff0
            )
        else:
            embed = discord.Embed(
                description=f"🌸 **{interaction.user.display_name}** gives a blushing sakura kiss to **{member.display_name}**! 💋",
                color=0xff9ff0
            )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)

    @actions_group.command(name="cuddle", description="🌸 Snuggle up with someone!")
    async def cuddle(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("cuddle")
        if not member:
            embed = discord.Embed(
                description="🌸 The sakura petals form a cozy nest around you! (っ˘̩╭╮˘̩)っ🌺",
                color=0xffb3de
            )
        else:
            embed = discord.Embed(
                description=f"🌸 **{interaction.user.display_name}** cuddles up with **{member.display_name}** under the cherry blossoms! 🌸",
                color=0xffb3de
            )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)

    @actions_group.command(name="slap", description="🌸 Give a petal-powered slap!")
    async def slap(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("slap")
        if not member:
            embed = discord.Embed(
                description="🌸 Why slap yourself? Let's settle this with flower tea instead! 🍵",
                color=0xff6666
            )
        else:
            embed = discord.Embed(
                description=f"🌸 **{interaction.user.display_name}** sends a sakura slap to **{member.display_name}**! 💢",
                color=0xff6666
            )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)

    @actions_group.command(name="punch", description="🌸 Throw a blossom-powered punch!")
    async def punch(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("punch")
        if not member:
            embed = discord.Embed(
                description="🌸 Punching the air? Let's release frustration with flower arranging instead! 💮",
                color=0xff4444
            )
        else:
            embed = discord.Embed(
                description=f"🌸 **{interaction.user.display_name}** throws a petal-powered punch at **{member.display_name}**! 🌸💥",
                color=0xff4444
            )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)

    @actions_group.command(name="proud", description="🌸 Show someone you're proud of them!")
    async def proud(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("anime proud")
        if not member:
            embed = discord.Embed(
                description="🌸 I'm proud of you! Every step forward is a petal in your journey! 🌸",
                color=0x77dd77
            )
        else:
            embed = discord.Embed(
                description=f"🌸 **{interaction.user.display_name}** is blooming proud of **{member.display_name}**! 🌸🏆",
                color=0x77dd77
            )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
        
    @actions_group.command(name="kill", description="💢 Express your angry to someone.")
    async def kill(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = random.choice(self.kill_gifs)
        if not member:
            embed = discord.Embed(
                description="😰 Oh no no no, i did nothing i swear 🙏😭",
                color=0xE50046
            )
        else:
            embed = discord.Embed(
                description=f"😰 Oh no, **{interaction.user.display_name}** is so mad at **{member.display_name}**! 💀☠️",
                color=0xE50046
            )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)

    @actions_group.command(name="lick", description="👅 Lick someone playfully!")
    async def lick(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("lick")
        embed = discord.Embed(
            description=f"👅 **{interaction.user.display_name}** gives {f'**{member.display_name}**' if member else 'a playful lick!'}",
            color=0xff69b4
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="nom", description="🍪 Give a cute nom to someone!")
    async def nom(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("nom")
        embed = discord.Embed(
            description=f"🍪 **{interaction.user.display_name}** noms {f'**{member.display_name}**' if member else 'something delicious!'}",
            color=0xffc0cb
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="pat", description="✨ Give a comforting head pat!")
    async def pat(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("pat")
        embed = discord.Embed(
            description=f"✨ **{interaction.user.display_name}** pats {f'**{member.display_name}**' if member else 'themselves for comfort!'}",
            color=0xffd700
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="poke", description="👉 Poke someone to grab their attention!")
    async def poke(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("poke")
        embed = discord.Embed(
            description=f"👉 **{interaction.user.display_name}** pokes {f'**{member.display_name}**' if member else 'the air!'}",
            color=0x87ceeb
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="stare", description="👀 Stare at someone intensely!")
    async def stare(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("stare")
        embed = discord.Embed(
            description=f"👀 **{interaction.user.display_name}** stares {f'at **{member.display_name}**' if member else 'into the void...'}",
            color=0x4682b4
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="highfive", description="✋ High-five someone!")
    async def highfive(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("highfive")
        embed = discord.Embed(
            description=f"✋ **{interaction.user.display_name}** high-fives {f'**{member.display_name}**!' if member else 'themselves... kinda awkward!'}",
            color=0xffff00
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="bite", description="🐺 Bite someone playfully!")
    async def bite(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("bite")
        embed = discord.Embed(
            description=f"🐺 **{interaction.user.display_name}** playfully bites {f'**{member.display_name}**' if member else 'thin air!'}",
            color=0x8b0000
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="greet", description="👋 Greet someone warmly!")
    async def greet(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("greet")
        embed = discord.Embed(
            description=f"👋 **{interaction.user.display_name}** greets {f'**{member.display_name}** warmly!' if member else 'everyone!'}",
            color=0x32cd32
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)

    @actions_group.command(name="handholding", description="🤝 Hold hands with someone!")
    async def handholding(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("handholding")
        embed = discord.Embed(
            description=f"🤝 **{interaction.user.display_name}** holds hands {f'with **{member.display_name}** ❤️' if member else 'with themselves... how?' }",
            color=0xff69b4
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="tickle", description="😆 Tickle someone and make them laugh!")
    async def tickle(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("tickle")
        embed = discord.Embed(
            description=f"😆 **{interaction.user.display_name}** tickles {f'**{member.display_name}**, making them giggle!' if member else 'the air... wait, what?'}",
            color=0xffd700
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="hold", description="🫂 Hold someone close!")
    async def hold(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("hold")
        embed = discord.Embed(
            description=f"🫂 **{interaction.user.display_name}** holds {f'**{member.display_name}** tightly!' if member else 'their pillow... so lonely!'}",
            color=0xffb6c1
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="pats", description="🐾 Give soft pats to someone!")
    async def pats(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("pats")
        embed = discord.Embed(
            description=f"🐾 **{interaction.user.display_name}** gives {f'gentle pats to **{member.display_name}**!' if member else 'themselves... cute!'}",
            color=0xffc0cb
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="wave", description="👋 Wave at someone!")
    async def wave(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("wave")
        embed = discord.Embed(
            description=f"👋 **{interaction.user.display_name}** waves {f'at **{member.display_name}**!' if member else 'at everyone!'}",
            color=0x87ceeb
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="boop", description="🐽 Boop someone's nose!")
    async def boop(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("boop")
        embed = discord.Embed(
            description=f"🐽 **{interaction.user.display_name}** boops {f'**{member.display_name}** on the nose!' if member else 'the air... adorable!'}",
            color=0xffdab9
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="snuggle", description="🤗 Snuggle up with someone warmly!")
    async def snuggle(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("snuggle")
        embed = discord.Embed(
            description=f"🤗 **{interaction.user.display_name}** snuggles {f'**{member.display_name}** closely!' if member else 'their blanket... cozy!'}",
            color=0xffa07a
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)
    
    @actions_group.command(name="bully", description="😈 Playfully bully someone!")
    async def bully(self, interaction: discord.Interaction, member: discord.Member = None):
        gif_url = await self.fetch_gif("bully")
        embed = discord.Embed(
            description=f"😈 **{interaction.user.display_name}** teases {f'**{member.display_name}** playfully!' if member else 'themselves... wait, what?'}",
            color=0x8b0000
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(content=member.mention if member else "", embed=embed)


async def setup(bot):
    await bot.add_cog(ActionCommands(bot))