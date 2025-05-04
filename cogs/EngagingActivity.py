import discord 
from discord import app_commands, Embed
from discord.ext import commands, tasks
import random 
import json
from utilities import get_emojis_variables, colors
from errors.error_logger import error_send
import time
import asyncio
from discord.ui import View, button, Button
from utilities import load_roles_ids

class TruthOrDareView(View):
    def __init__(self, bot, data_path):
        super().__init__(timeout=None)
        self.bot = bot
        self.data_path = data_path

    @button(label="Play", style=discord.ButtonStyle.green, emoji="😈")
    async def play_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        
        # Load the data
        with open(self.data_path, "r") as f:
            data = json.load(f)

        category = random.choice(["truths", "dares"])
        prev_key = f"previous_{category}"
        questions = data[category]
        previous = data[prev_key]

        remaining = [q for i, q in enumerate(questions) if str(i) not in previous]
        if not remaining:
            data[prev_key] = []
            remaining = questions

        question = random.choice(remaining)
        data[prev_key].append(str(questions.index(question)))

        with open(self.data_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        embed = interaction.message.embeds[0]
        embed.description = f"{interaction.user.mention} **{category[:-1].capitalize()} picked!**\n{question}"
        embed.color = colors.primary
        await interaction.channel.send(
            embed=embed,
            view=TruthOrDareView(self.bot, self.data_path),
            allowed_mentions=discord.AllowedMentions(users=True)
        )


class EngageActivity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.post_channels = [1349150427106508821]
        self.emojis = get_emojis_variables()
        
        # Games
        self.trivi_games = {}
        self.duration = 60
        self.Engage.start()
        
    def get_question(self, file_path):
        # Load questions data
        with open(file_path, "r") as f:
            questions_data = json.load(f)
        
        # Pick a random question from the list and ignore the already asked questions 
        question = random.choice(questions_data["questions"])
        while str(questions_data["questions"].index(question)) in questions_data["previous_q"]:
            if len(questions_data["previous_q"]) == len(questions_data["questions"]):
                questions_data["previous_q"] = []
                print("empty")
            question = random.choice(questions_data["questions"])
        questions_data["previous_q"].append(str(questions_data["questions"].index(question)))
        # Update the questions data 
        with open(file_path, "w") as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)
        return question 
        
    # Task function to pick an activity every period of time 
    @tasks.loop(hours=2)
    async def Engage(self):
        try:
            print("Engage Function")
            activities = ["FunQ", "FunPoll", "TruthOrDare", "Trivia"]
            with open("./configs/channels/channels_id.json", "r") as f:
                data = json.load(f)
                self.post_channels = data.get("engage_post_channels", self.post_channels)
                print("post channel:",self.post_channels)
            for channel_id in self.post_channels:
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    continue 
                activity = random.choice(activities)
                if activity == "FunQ":
                    await self.FunQuestion(channel)
                if activity == "FunPoll":
                    await self.FunPoll(channel)
                if activity == "Trivia":
                    await self.Trivia(channel)
                if activity == "TruthOrDare":
                    await self.TruthOrDare(channel)
                await asyncio.sleep(1)
        except Exception:
            await error_send()

    @app_commands.command(name="engage", description="Send an engaging activity!")
    @app_commands.choices(
        activity=[
            app_commands.Choice(name="Random", value="random"),
            app_commands.Choice(name="Fun Questions", value="FunQ"),
            app_commands.Choice(name="Fun Poll", value="FunPoll"),
            app_commands.Choice(name="Trivia", value="Trivia"),
            app_commands.Choice(name="Truth Or Dare", value="TruthOrDare")
        ]
    )
    async def engage_command(self, interaction: discord.Interaction, activity: app_commands.Choice[str], channel: discord.TextChannel = None):
        channel = interaction.channel if not channel else channel
        activities = [
               "FunQ", "FunPoll", "TruthOrDare", "Trivia"
        ]
        activity = random.choice(activities) if activity.value == "random" else activity.value
        if activity == "FunQ":
            await self.FunQuestion(channel)
        if activity == "FunPoll":
            await self.FunPoll(channel)
        if activity == "Trivia":
            await self.Trivia(channel)
        if activity == "TruthOrDare":
            await self.TruthOrDare(channel)
        await interaction.response.send_message(f"Sent in {channel.mention}", ephemeral=True)
    
    
    # random question activity 
    async def FunQuestion(self, channel):
        # Get question and update questions_data
        question = self.get_question("./configs/ActivityQuestion.json")
        # get channel using bot object
        await channel.send(f"{self.emojis["HeartMessage"]} **Fun Question:** {question}")

    # Random poll
    async def FunPoll(self, channel):
        poll = self.get_question("./configs/PollQuestions.json")
        await channel.send(f"{self.emojis["LikeHeart"]} **Quick Poll!** {poll}")
        
    # Truth or Dare
    async def TruthOrDare(self, channel):
        view = TruthOrDareView(self.bot, "./configs/TruthOrDare.json")
        sentence = random.choice([
            "Click the button below if you're brave enough.",
            "Want test your luck? click the button below and don't complain if it's a hot dare 😈",
            "Click to see if it's truth or dare! but you'll have to do whatever I'm hiding 😘"
        ])
        embed = Embed(
            title=f"{self.emojis["emoji_skull"]} Truth or Dare Time!",
            description=sentence,
            color=colors.purple
        )
        await channel.send(embed=embed, view=view)
    
    # Random trivia questions 
    async def Trivia(self, channel):
        data = self.get_question("./configs/TriviaQuestions.json")
        question = data["question"]
        options = []
        options = list(data["options"].keys())
        # send embed
        embed = Embed(
            title=f"{self.emojis["CatHeart"]} Quick Trivia Question!",
            description=f"""
{self.emojis["FoxHi"]} **Question:** {question}
{self.emojis["TwoHearts"]} **Options** 
🩵  • {options[0]}
🤍  • {options[1]}
🩷  • {options[2]}
            """,
            color=colors.softpink
        )
        embed.set_footer(text=f"Duration: {self.duration} seconds")
        message = await channel.send(embed=embed)
        # Add the options to the game 
        self.trivi_games[channel.id] = {
            "data": data,
            "message_id": message.id,
            "event": asyncio.Event(),
            "blacklist": []
        }
        emojis = ["🩵","🤍","🩷"]
        for emoji in emojis:
            await message.add_reaction(emoji)
        correct_answer = ""
        
        for option in data["options"]:
            if data["options"][option] == True:
                correct_answer = option
                
        try:
            await asyncio.wait_for(self.trivi_games[channel.id]["event"].wait(), timeout=self.duration)
            embed.color = colors.green
            embed.set_footer(text=f"Answered! The answer is {correct_answer}")
            await message.edit(embed=embed)
        except asyncio.TimeoutError:
            # Time is over
            embed.color = colors.red
            embed.title = f"{self.emojis["BlackCatHeart"]} Quick Trivia Question! (Time is over)"
            embed.set_footer(text=f"Finished. The answer was {correct_answer}")
            await message.edit(embed=embed)
            del self.trivi_games[channel.id]
            
        await asyncio.sleep(60)
        await message.delete()
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        try:
            channel_id = reaction.message.channel.id
            message_id = reaction.message.id
            # ignore bots 
            if user.bot:
                return 
            # ignore if no trivia game
            if channel_id not in self.trivi_games:
                return 
            # ignore it no trivia game in that channel 
            if not self.trivi_games[channel_id]:
                return 
            # ignore if not reacted to the bot message 
            game_message_id = self.trivi_games[channel_id]["message_id"]
            if message_id != game_message_id:
                return 
            # If the reaction not one of the given reactions
            emojis = ["🩵","🤍","🩷"]
            if reaction.emoji not in emojis:
                return 
            # extract data and the options
            data = self.trivi_games[channel_id]["data"]
            options_names = list(data["options"].keys())
            channel = reaction.message.channel
            if user.id in self.trivi_games[channel_id]["blacklist"]:
                await channel.send(f"{self.emojis["emoji_forbidden"]} {user.mention} don't have chances to answer", delete_after=10)
                return 
            # Check if the reaction is the correct one
            is_correct = data["options"][options_names[emojis.index(reaction.emoji)]]
            if is_correct:
                await channel.send(f"{self.emojis['Crown']} {user.mention} Your answer is correct!", delete_after=20) 
                self.trivi_games[channel_id]["event"].set() 
                del self.trivi_games[channel_id]
            else:
                self.trivi_games[channel_id]["blacklist"].append(user.id)
                await channel.send(f"{self.emojis["emoji_forbidden"]} {user.mention} Your answer is **not** correct.", delete_after=10)
                
        except Exception:
            await error_send()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return 
        try:
            # Auto react to triggers
            triggers = ["welcome", "wlc", "love you", "luv u", "luv you"]
            is_triggered = False
            for trigger in triggers:
                if trigger in message.content:
                    is_triggered = True
            if is_triggered:
                reactions = [
                    self.emojis["redglassheart"],
                    self.emojis["PinkHearts"],
                    self.emojis["blowingHearts"],
                    self.emojis["TwoHearts"],
                    self.emojis["HeartMessage"],
                    self.emojis["PurpleHearts"],
                    self.emojis["Heartribbon"],
                    self.emojis["Heartspin"],
                    self.emojis["CatHeart"],
                    self.emojis["BlackCatHeart"],
                    self.emojis["LikeHeart"],
                ]
                reaction = random.choice(reactions)
                try: 
                    await message.add_reaction(reaction)
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    pass
                except Exception:
                    await error_send()
            
            # add random reaction to messages 
            react = random.choices(
                [True, False],
                weights=[0.02, 0.98],
                k=1
            )[0]
            if react:
                emojis = ["💀", "😭", "😶‍🌫️", "🤡", "😩", "😵‍💫", "😹", "🤣", "🙃", "😈", "👀", "🥴", "😵", "😬", "😳", "😤", "🗿", "😛", "😒", "😔", "💅", "🧍", "🧎", "😎", "🤓"]
                await message.add_reaction(random.choice(emojis))
        except Exception:
            await error_send()
    
async def setup(bot):
    cog = EngageActivity(bot)
    await bot.add_cog(cog)