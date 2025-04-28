import discord
from discord import app_commands
from discord.ext import commands
import logging
import random
import asyncio
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.db_manager import DatabaseManager
from utilities.variables import get_emojis_variables

logger = logging.getLogger('bot.games')

# Get custom emojis
emojis = get_emojis_variables()

# Define the main theme color (red)
THEME_COLOR = discord.Color.from_str("#c40000")

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.games_on_cooldown = {}
    
    # Helper methods
    async def create_embed(self, title, description, color=discord.Color.blue(), footer=None, fields=None, thumbnail=None):
        """Create a Discord embed"""
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
        
        if footer:
            embed.set_footer(text=footer)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        if fields:
            for field in fields:
                embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', True))
        
        return embed
    
    async def check_cooldown(self, user_id, game_name, cooldown_seconds=60):
        """Check if a user is on cooldown for a specific game"""
        key = f"{user_id}_{game_name}"
        
        if key in self.games_on_cooldown:
            cooldown_end = self.games_on_cooldown[key]
            if datetime.now() < cooldown_end:
                time_left = cooldown_end - datetime.now()
                return False, int(time_left.total_seconds())
        
        # Set cooldown
        self.games_on_cooldown[key] = datetime.now() + timedelta(seconds=cooldown_seconds)
        return True, 0
    
    # Minigames
    @app_commands.command(name="coinflip", description="Flip a coin and bet SFlirts")
    @app_commands.describe(
        bet="Amount of SFlirts to bet",
        choice="Choose heads or tails"
    )
    @app_commands.choices(choice=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, choice: str):
        """Flip a coin and bet SFlirts"""
        try:
            # Check cooldown
            can_play, seconds_left = await self.check_cooldown(interaction.user.id, "coinflip", 30)
            if not can_play:
                await interaction.response.send_message(f"You need to wait {seconds_left} seconds before using this command again.", ephemeral=True)
                return
            
            # Check bet amount
            if bet <= 0:
                await interaction.response.send_message("Your bet must be greater than 0 SFlirts.", ephemeral=True)
                return
            
            # Get user
            user_data = self.db.get_user(interaction.user.id)
            
            # Check if user has enough money
            if user_data['balance'] < bet:
                await interaction.response.send_message("You don't have enough SFlirts for this bet.", ephemeral=True)
                return
            
            # Get coin emoji
            coin_emoji = emojis["sflirt_coin"]
            
            # Send initial message
            embed = await self.create_embed(
                title=f"{emojis['redglassheart']} Coin Flip",
                description=f"{interaction.user.mention} bet {bet} {coin_emoji} on {choice}!\n\nFlipping coin...",
                color=THEME_COLOR
            )
            await interaction.response.send_message(embed=embed)
            
            # Wait for suspense
            await asyncio.sleep(2)
            
            # Determine result
            result = random.choice(["heads", "tails"])
            
            # Update embed based on result
            if result == choice.lower():
                # Win (2x bet)
                winnings = bet
                self.db.record_game_win(interaction.user.id, winnings)
                
                embed = await self.create_embed(
                    title=f"{emojis['PinkHearts']} Coin Flip - You Won!",
                    description=f"The coin landed on **{result.upper()}**!\n\n{interaction.user.mention} won {winnings} {coin_emoji}!",
                    color=discord.Color.green(),
                    fields=[
                        {"name": "Your choice", "value": choice.capitalize()},
                        {"name": "Result", "value": result.capitalize()},
                        {"name": "Winnings", "value": f"+{winnings} {coin_emoji}"}
                    ]
                )
            else:
                # Loss
                self.db.record_game_loss(interaction.user.id, bet)
                
                embed = await self.create_embed(
                    title=f"{emojis['BlackCatHeart']} Coin Flip - You Lost!",
                    description=f"The coin landed on **{result.upper()}**!\n\n{interaction.user.mention} lost {bet} {coin_emoji}!",
                    color=discord.Color.red(),
                    fields=[
                        {"name": "Your choice", "value": choice.capitalize()},
                        {"name": "Result", "value": result.capitalize()},
                        {"name": "Loss", "value": f"-{bet} {coin_emoji}"}
                    ]
                )
            
            await interaction.edit_original_response(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in coinflip game: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
    
    @app_commands.command(name="slots", description="Play the slot machine with SFlirts")
    @app_commands.describe(bet="Amount of SFlirts to bet")
    async def slots(self, interaction: discord.Interaction, bet: int):
        """Play the slot machine with SFlirts"""
        try:
            # Check cooldown
            can_play, seconds_left = await self.check_cooldown(interaction.user.id, "slots", 45)
            if not can_play:
                await interaction.response.send_message(f"You need to wait {seconds_left} seconds before using this command again.", ephemeral=True)
                return
            
            # Check bet amount
            if bet <= 0:
                await interaction.response.send_message("Your bet must be greater than 0 SFlirts.", ephemeral=True)
                return
            
            # Get user
            user_data = self.db.get_user(interaction.user.id)
            
            # Check if user has enough money
            if user_data['balance'] < bet:
                await interaction.response.send_message("You don't have enough SFlirts for this bet.", ephemeral=True)
                return
            
            # Get coin emoji
            coin_emoji = emojis["sflirt_coin"]
            
            # Send initial message
            embed = await self.create_embed(
                title=f"🎰 {emojis['TwoHearts']} Slot Machine {emojis['TwoHearts']} 🎰",
                description=f"{interaction.user.mention} bet {bet} {coin_emoji}!\n\n{emojis['HeartPopUp']} Spinning...",
                color=THEME_COLOR
            )
            await interaction.response.send_message(embed=embed)
            
            # Wait for suspense
            await asyncio.sleep(2)
            
            # Slot machine symbols - using our beautiful heart emojis where possible
            symbols = [emojis["redglassheart"], "💋", "🌹", "💎", emojis["Heartspin"], "🍒", "7️⃣"]
            weights = [20, 20, 15, 15, 12, 10, 8]  # Different weights for each symbol
            
            # Generate slot results
            slots = []
            for _ in range(3):
                slots.append(random.choices(symbols, weights=weights, k=1)[0])
            
            # Check results
            if slots[0] == slots[1] == slots[2]:
                # Jackpot - all three match
                if slots[0] == "7️⃣":
                    # Super jackpot with 7s
                    multiplier = 10
                    result_text = f"{emojis['Crown']} SUPER JACKPOT! Three 7s! {emojis['Crown']}"
                else:
                    # Regular jackpot
                    multiplier = 5
                    result_text = f"{emojis['PinkHearts']} JACKPOT! Three matching symbols! {emojis['PinkHearts']}"
            elif slots[0] == slots[1] or slots[1] == slots[2] or slots[0] == slots[2]:
                # Two matching symbols
                multiplier = 2
                result_text = f"{emojis['CatHeart']} NICE! Two matching symbols! {emojis['CatHeart']}"
            else:
                # No matches
                multiplier = 0
                result_text = f"{emojis['BlackCatHeart']} No matches. Better luck next time!"
            
            # Calculate winnings
            winnings = bet * multiplier
            
            # Update balance
            if multiplier > 0:
                self.db.record_game_win(interaction.user.id, winnings - bet)  # Subtract bet since we're adding the net win
                result_color = discord.Color.green()
            else:
                self.db.record_game_loss(interaction.user.id, bet)
                result_color = discord.Color.red()
            
            # Update embed with results
            slots_display = f"[ {slots[0]} | {slots[1]} | {slots[2]} ]"
            
            if multiplier > 0:
                description = f"{result_text}\n\n{slots_display}\n\n{interaction.user.mention} won {winnings} {coin_emoji}!"
            else:
                description = f"{result_text}\n\n{slots_display}\n\n{interaction.user.mention} lost {bet} {coin_emoji}!"
            
            embed = await self.create_embed(
                title=f"🎰 {emojis['Heartribbon']} Slot Machine Results {emojis['Heartribbon']} 🎰",
                description=description,
                color=result_color,
                fields=[
                    {"name": "Bet", "value": f"{bet} {coin_emoji}"},
                    {"name": "Multiplier", "value": f"x{multiplier}"},
                    {"name": "Result", "value": f"{'+' if multiplier > 0 else '-'}{winnings if multiplier > 0 else bet} {coin_emoji}"}
                ]
            )
            
            await interaction.edit_original_response(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in slots game: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
    
    @app_commands.command(name="roulette", description="Play roulette with SFlirts")
    @app_commands.describe(
        bet="Amount of SFlirts to bet",
        bet_type="Type of bet to place",
        choice="Your choice based on bet type"
    )
    @app_commands.choices(bet_type=[
        app_commands.Choice(name="Color (Red/Black)", value="color"),
        app_commands.Choice(name="Even/Odd", value="parity"),
        app_commands.Choice(name="High/Low", value="range"),
        app_commands.Choice(name="Single Number (0-36)", value="number")
    ])
    async def roulette(self, interaction: discord.Interaction, bet: int, bet_type: str, choice: str):
        """Play roulette with SFlirts"""
        try:
            # Check cooldown
            can_play, seconds_left = await self.check_cooldown(interaction.user.id, "roulette", 60)
            if not can_play:
                await interaction.response.send_message(f"You need to wait {seconds_left} seconds before using this command again.", ephemeral=True)
                return
            
            # Check bet amount
            if bet <= 0:
                await interaction.response.send_message("Your bet must be greater than 0 SFlirts.", ephemeral=True)
                return
            
            # Get user
            user_data = self.db.get_user(interaction.user.id)
            
            # Check if user has enough money
            if user_data['balance'] < bet:
                await interaction.response.send_message("You don't have enough SFlirts for this bet.", ephemeral=True)
                return
            
            # Validate choice based on bet type
            valid_choice = False
            if bet_type == "color" and choice.lower() in ["red", "black"]:
                valid_choice = True
                multiplier = 2
            elif bet_type == "parity" and choice.lower() in ["even", "odd"]:
                valid_choice = True
                multiplier = 2
            elif bet_type == "range" and choice.lower() in ["high", "low"]:
                valid_choice = True
                multiplier = 2
            elif bet_type == "number" and choice.isdigit() and 0 <= int(choice) <= 36:
                valid_choice = True
                multiplier = 36
            
            if not valid_choice:
                await interaction.response.send_message("Invalid choice for the selected bet type.", ephemeral=True)
                return
            
            # Get coin emoji
            coin_emoji = emojis["sflirt_coin"]
            
            # Send initial message
            embed = await self.create_embed(
                title=f"🎲 {emojis['Heartspin']} Roulette {emojis['Heartspin']} 🎲",
                description=f"{interaction.user.mention} bet {bet} {coin_emoji} on {choice} ({bet_type})!\n\n{emojis['HeartMessage']} Spinning the wheel...",
                color=THEME_COLOR
            )
            await interaction.response.send_message(embed=embed)
            
            # Wait for suspense
            await asyncio.sleep(2)
            
            # Determine result
            result_number = random.randint(0, 36)
            
            # Determine colors (0 is green, odd numbers are red, even are black)
            if result_number == 0:
                result_color = "green"
            elif result_number % 2 == 1:
                result_color = "red"
            else:
                result_color = "black"
            
            # Determine if high or low (1-18 is low, 19-36 is high, 0 is neither)
            if result_number == 0:
                result_range = "zero"
            elif 1 <= result_number <= 18:
                result_range = "low"
            else:
                result_range = "high"
            
            # Determine if even or odd (0 is neither)
            if result_number == 0:
                result_parity = "zero"
            elif result_number % 2 == 0:
                result_parity = "even"
            else:
                result_parity = "odd"
            
            # Determine if player won
            won = False
            if bet_type == "color" and choice.lower() == result_color:
                won = True
            elif bet_type == "parity" and choice.lower() == result_parity:
                won = True
            elif bet_type == "range" and choice.lower() == result_range:
                won = True
            elif bet_type == "number" and int(choice) == result_number:
                won = True
            
            # Calculate winnings
            if won:
                winnings = bet * multiplier
                self.db.record_game_win(interaction.user.id, winnings - bet)
                result_text = f"{emojis['TwoHearts']} YOU WON! Ball landed on {result_number} ({result_color})! {emojis['redglassheart']}"
                result_color_embed = discord.Color.green()
            else:
                winnings = 0
                self.db.record_game_loss(interaction.user.id, bet)
                result_text = f"{emojis['BlackCatHeart']} YOU LOST! Ball landed on {result_number} ({result_color})."
                result_color_embed = discord.Color.red()
            
            # Create color emoji
            if result_color == "red":
                color_emoji = "🔴"
            elif result_color == "black":
                color_emoji = "⚫"
            else:
                color_emoji = "🟢"
            
            # Update embed with results
            if won:
                description = f"{result_text}\n\n{color_emoji} **{result_number}**\n\n{interaction.user.mention} won {winnings} {coin_emoji}!"
            else:
                description = f"{result_text}\n\n{color_emoji} **{result_number}**\n\n{interaction.user.mention} lost {bet} {coin_emoji}!"
            
            embed = await self.create_embed(
                title=f"🎲 {emojis['PurpleHearts']} Roulette Results {emojis['PurpleHearts']} 🎲",
                description=description,
                color=result_color_embed,
                fields=[
                    {"name": "Your Bet", "value": f"{choice} ({bet_type})"},
                    {"name": "Bet Amount", "value": f"{bet} {coin_emoji}"},
                    {"name": "Result", "value": f"{result_number} ({result_color}, {result_parity}, {result_range})"},
                    {"name": "Outcome", "value": f"{'Won' if won else 'Lost'} {winnings if won else bet} {coin_emoji}"}
                ]
            )
            
            await interaction.edit_original_response(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in roulette game: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
    
    @app_commands.command(name="love", description="Test love compatibility and win SFlirts")
    @app_commands.describe(user="The user to test love compatibility with")
    async def love(self, interaction: discord.Interaction, user: discord.User):
        """Test love compatibility with another user and win SFlirts"""
        try:
            # Check cooldown
            can_play, seconds_left = await self.check_cooldown(interaction.user.id, "love", 180)  # 3 minute cooldown
            if not can_play:
                await interaction.response.send_message(f"You need to wait {seconds_left} seconds before using this command again.", ephemeral=True)
                return
            
            # Can't test with yourself or a bot
            if user.id == interaction.user.id:
                await interaction.response.send_message("You can't test love compatibility with yourself!", ephemeral=True)
                return
            
            if user.bot:
                await interaction.response.send_message("You can't test love compatibility with a bot!", ephemeral=True)
                return
            
            # Get coin emoji
            coin_emoji = emojis["sflirt_coin"]
            
            # Send initial message
            embed = await self.create_embed(
                title=f"{emojis['redglassheart']} Love Compatibility Test {emojis['redglassheart']}",
                description=f"Testing love compatibility between {interaction.user.mention} and {user.mention}...",
                color=THEME_COLOR
            )
            await interaction.response.send_message(embed=embed)
            
            # Wait for suspense
            await asyncio.sleep(3)
            
            # Calculate a consistent love score based on user IDs
            # This ensures the same pair always gets the same result
            combined_id = str(min(interaction.user.id, user.id)) + str(max(interaction.user.id, user.id))
            seed = int(combined_id) % 10000
            random.seed(seed)
            
            # Generate love score (0-100)
            love_score = random.randint(0, 100)
            
            # Determine reward based on score
            if love_score >= 90:  # Perfect match
                reward = random.randint(100, 150)
                message = f"{emojis['PinkHearts']} Perfect Match! {emojis['PinkHearts']}"
                description = f"Wow! {interaction.user.mention} and {user.mention} are a perfect match made in heaven!"
            elif love_score >= 70:  # Great match
                reward = random.randint(70, 100)
                message = f"{emojis['TwoHearts']} Great Match! {emojis['TwoHearts']}"
                description = f"{interaction.user.mention} and {user.mention} have amazing chemistry together!"
            elif love_score >= 50:  # Good match
                reward = random.randint(40, 70)
                message = f"{emojis['HeartMessage']} Good Match! {emojis['HeartMessage']}"
                description = f"{interaction.user.mention} and {user.mention} could definitely be something special!"
            elif love_score >= 30:  # Okay match
                reward = random.randint(20, 40)
                message = f"{emojis['LikeHeart']} Decent Match {emojis['LikeHeart']}"
                description = f"{interaction.user.mention} and {user.mention} might work with some effort."
            else:  # Poor match
                reward = random.randint(5, 20)
                message = f"{emojis['BlackCatHeart']} Not Compatible {emojis['BlackCatHeart']}"
                description = f"Sorry, {interaction.user.mention} and {user.mention} might be better as friends."
            
            # Grant the reward to the user who initiated the test
            self.db.record_game_win(interaction.user.id, reward)
            
            # Generate heart display based on love score - use custom emoji for filled hearts
            hearts_filled = int(love_score / 10)
            hearts_empty = 10 - hearts_filled
            heart_meter = f"{emojis['redglassheart']}" * hearts_filled + "🖤" * hearts_empty
            
            # Update embed with results
            embed = await self.create_embed(
                title=f"{emojis['blowingHearts']} Love Compatibility: {love_score}% {emojis['blowingHearts']}",
                description=f"{description}\n\n{heart_meter}\n\n{message}\n\n{interaction.user.mention} received {reward} {coin_emoji} for the test!",
                color=THEME_COLOR,
                fields=[
                    {"name": "Love Score", "value": f"{love_score}%"},
                    {"name": "Reward", "value": f"{reward} {coin_emoji}"}
                ]
            )
            
            # Reset random seed
            random.seed()
            
            await interaction.edit_original_response(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in love compatibility test: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
    
    @app_commands.command(name="hangman", description="Play hangman to earn SFlirts")
    async def hangman(self, interaction: discord.Interaction):
        """Play hangman to earn SFlirts"""
        try:
            # Check cooldown
            can_play, seconds_left = await self.check_cooldown(interaction.user.id, "hangman", 300)  # 5 minute cooldown
            if not can_play:
                await interaction.response.send_message(f"You need to wait {seconds_left} seconds before using this command again.", ephemeral=True)
                return
            
            # Dating-themed words for hangman
            dating_words = [
                "romance", "dating", "couple", "partner", "relationship", 
                "flirting", "love", "crush", "valentine", "kiss", 
                "cuddle", "date", "attraction", "boyfriend", "girlfriend",
                "marriage", "proposal", "anniversary", "dinner", "flowers",
                "chocolate", "compliment", "soulmate", "affection", "infatuation"
            ]
            
            # Choose a random word
            word = random.choice(dating_words).upper()
            guessed_letters = set()
            wrong_guesses = 0
            max_wrong = 6  # Number of wrong guesses allowed
            
            # Hangman ASCII art stages
            hangman_stages = [
                "```\n      \n      \n      \n      \n      \n_______```",
                "```\n      \n |    \n |    \n |    \n |    \n_|_____```",
                "```\n  ___ \n |    \n |    \n |    \n |    \n_|_____```",
                "```\n  ___ \n |  O \n |    \n |    \n |    \n_|_____```",
                "```\n  ___ \n |  O \n |  | \n |    \n |    \n_|_____```",
                "```\n  ___ \n |  O \n | /|\\\n |    \n |    \n_|_____```",
                "```\n  ___ \n |  O \n | /|\\\n | / \\\n |    \n_|_____```"
            ]
            
            # Function to display the current state of the word
            def get_word_display():
                display = ""
                for letter in word:
                    if letter in guessed_letters:
                        display += letter + " "
                    else:
                        display += "_ "
                return display.strip()
            
            # Get coin emoji
            coin_emoji = emojis["sflirt_coin"]
            
            # Initial embed
            embed = discord.Embed(
                title=f"{emojis['PurpleHearts']} Dating Hangman {emojis['PurpleHearts']}",
                description=f"{interaction.user.mention} is playing hangman to win {coin_emoji}!\n\n{emojis['FoxHi']} Guess letters by using the buttons below.",
                color=THEME_COLOR,
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Word", value=f"```{get_word_display()}```", inline=False)
            embed.add_field(name="Guessed Letters", value="None", inline=False)
            embed.add_field(name="Wrong Guesses", value=f"{wrong_guesses}/{max_wrong}", inline=False)
            embed.add_field(name="Hangman", value=hangman_stages[wrong_guesses], inline=False)
            
            # Create letter buttons
            buttons = []
            for letter_ascii in range(65, 91):  # A-Z ASCII values
                letter = chr(letter_ascii)
                buttons.append(discord.ui.Button(label=letter, custom_id=f"hangman_{letter}"))
            
            # Create action row views (5 buttons per row)
            view = discord.ui.View(timeout=180)  # 3 minute timeout
            for i in range(0, len(buttons), 5):
                for button in buttons[i:i+5]:
                    view.add_item(button)
            
            # Send initial message with buttons
            await interaction.response.send_message(embed=embed, view=view)
            
            # Game state tracking
            game_over = False
            won = False
            
            # Wait for button interactions
            def check(i):
                return i.data["custom_id"].startswith("hangman_") and i.user.id == interaction.user.id
            
            # Game loop
            while not game_over and wrong_guesses < max_wrong:
                try:
                    # Wait for a button press
                    button_interaction = await self.bot.wait_for("interaction", check=check, timeout=180)
                    
                    # Get the letter from the button
                    letter = button_interaction.data["custom_id"].split("_")[1]
                    
                    # Add to guessed letters
                    guessed_letters.add(letter)
                    
                    # Check if letter is in the word
                    if letter in word:
                        # Correct guess
                        # Check if word is complete
                        if all(letter in guessed_letters for letter in word):
                            game_over = True
                            won = True
                    else:
                        # Wrong guess
                        wrong_guesses += 1
                        if wrong_guesses >= max_wrong:
                            game_over = True
                    
                    # Update embed
                    embed = discord.Embed(
                        title=f"{emojis['PurpleHearts']} Dating Hangman {emojis['PurpleHearts']}",
                        description=f"{interaction.user.mention} is playing hangman to win {coin_emoji}!\n\n{emojis['FoxHi']} Guess letters by using the buttons below.",
                        color=THEME_COLOR,
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(name="Word", value=f"```{get_word_display()}```", inline=False)
                    embed.add_field(name="Guessed Letters", value=", ".join(sorted(guessed_letters)) or "None", inline=False)
                    embed.add_field(name="Wrong Guesses", value=f"{wrong_guesses}/{max_wrong}", inline=False)
                    embed.add_field(name="Hangman", value=hangman_stages[wrong_guesses], inline=False)
                    
                    # Update view (disable guessed buttons)
                    new_view = discord.ui.View(timeout=180)
                    for i in range(0, len(buttons), 5):
                        for button in buttons[i:i+5]:
                            letter = button.custom_id.split("_")[1]
                            button.disabled = letter in guessed_letters or game_over
                            new_view.add_item(button)
                    
                    # Handle game over states
                    if game_over:
                        if won:
                            # Calculate reward based on wrong guesses
                            reward = 150 - (wrong_guesses * 20)  # Max 150, min 30
                            self.db.record_game_win(interaction.user.id, reward)
                            
                            embed.title = f"{emojis['PinkHearts']} Dating Hangman - You Won! {emojis['PinkHearts']}"
                            embed.description = f"{emojis['TwoHearts']} Congratulations! You correctly guessed the word!\n\nThe word was: **{word}**\n\nYou earned {reward} {coin_emoji}!"
                            embed.color = discord.Color.green()
                        else:
                            embed.title = f"{emojis['BlackCatHeart']} Dating Hangman - You Lost! {emojis['BlackCatHeart']}"
                            embed.description = f"{emojis['offline']} Oh no! You ran out of guesses!\n\nThe word was: **{word}**"
                            embed.color = discord.Color.red()
                    
                    # Update the message
                    await button_interaction.response.edit_message(embed=embed, view=new_view)
                
                except asyncio.TimeoutError:
                    # Game timed out
                    embed.title = f"{emojis['offline']} Dating Hangman - Timed Out {emojis['offline']}"
                    embed.description = f"Game timed out due to inactivity.\n\nThe word was: **{word}**"
                    embed.color = THEME_COLOR
                    
                    # Disable all buttons
                    for button in view.children:
                        button.disabled = True
                    
                    await interaction.edit_original_response(embed=embed, view=view)
                    game_over = True
                    break
            
        except Exception as e:
            logger.error(f"Error in hangman game: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
    
    @app_commands.command(name="trivia", description="Answer dating trivia questions to earn SFlirts")
    async def trivia(self, interaction: discord.Interaction):
        """Play dating trivia to earn SFlirts"""
        try:
            # Check cooldown
            can_play, seconds_left = await self.check_cooldown(interaction.user.id, "trivia", 120)  # 2 minute cooldown
            if not can_play:
                await interaction.response.send_message(f"You need to wait {seconds_left} seconds before using this command again.", ephemeral=True)
                return
            
            # Dating trivia questions
            dating_trivia = [
                {
                    "question": "What is traditionally considered the most romantic day of the year?",
                    "answers": ["Valentine's Day", "February 14th", "Valentine's"],
                    "correct": "Valentine's Day"
                },
                {
                    "question": "What flower is traditionally associated with love and romance?",
                    "answers": ["Rose", "Roses", "Red Rose", "Red Roses"],
                    "correct": "Rose"
                },
                {
                    "question": "What is the traditional gift for a 25th wedding anniversary?",
                    "answers": ["Silver", "Silver Anniversary"],
                    "correct": "Silver"
                },
                {
                    "question": "In which city is the famous 'Love Lock Bridge' (Pont des Arts) located?",
                    "answers": ["Paris", "Paris, France"],
                    "correct": "Paris"
                },
                {
                    "question": "What is the name of the Greek goddess of love?",
                    "answers": ["Aphrodite"],
                    "correct": "Aphrodite"
                },
                {
                    "question": "What is the name of Cupid's mother in Roman mythology?",
                    "answers": ["Venus"],
                    "correct": "Venus"
                },
                {
                    "question": "What gemstone is traditionally associated with engagement rings?",
                    "answers": ["Diamond", "Diamonds"],
                    "correct": "Diamond"
                },
                {
                    "question": "In which Shakespeare play does the famous balcony scene occur?",
                    "answers": ["Romeo and Juliet", "Romeo & Juliet"],
                    "correct": "Romeo and Juliet"
                },
                {
                    "question": "What is the traditional gift for a first wedding anniversary?",
                    "answers": ["Paper"],
                    "correct": "Paper"
                },
                {
                    "question": "What hormone is often called the 'love hormone'?",
                    "answers": ["Oxytocin"],
                    "correct": "Oxytocin"
                }
            ]
            
            # Choose a random question
            question_data = random.choice(dating_trivia)
            
            # Get coin emoji
            coin_emoji = emojis["sflirt_coin"]
            
            # Create embed
            embed = await self.create_embed(
                title=f"{emojis['PurpleHearts']} Dating Trivia {emojis['PurpleHearts']}",
                description=f"Answer correctly to win {coin_emoji}!\n\n{emojis['Thinking']} **Question:**\n{question_data['question']}\n\n{emojis['Writing']} Type your answer below!",
                color=THEME_COLOR,
                footer="You have 30 seconds to answer!"
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Wait for the answer
            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
            
            try:
                message = await self.bot.wait_for("message", check=check, timeout=30.0)
                
                # Check if the answer is correct (case insensitive)
                user_answer = message.content.strip().lower()
                correct_answers = [answer.lower() for answer in question_data["answers"]]
                
                if user_answer in correct_answers:
                    # Correct answer
                    reward = random.randint(30, 50)
                    self.db.record_game_win(interaction.user.id, reward)
                    
                    embed = await self.create_embed(
                        title=f"{emojis['PinkHearts']} Dating Trivia - Correct! {emojis['PinkHearts']}",
                        description=f"{emojis['TwoHearts']} Correct answer! The answer was **{question_data['correct']}**.\n\nYou earned {reward} {coin_emoji}!",
                        color=discord.Color.green()
                    )
                else:
                    # Wrong answer
                    embed = await self.create_embed(
                        title=f"{emojis['BlackCatHeart']} Dating Trivia - Incorrect! {emojis['BlackCatHeart']}",
                        description=f"{emojis['offline']} Sorry, that's not correct. The answer was **{question_data['correct']}**.",
                        color=discord.Color.red()
                    )
                
                await interaction.followup.send(embed=embed)
            
            except asyncio.TimeoutError:
                # Time ran out
                embed = await self.create_embed(
                    title=f"{emojis['offline']} Dating Trivia - Time's Up! {emojis['offline']}",
                    description=f"{emojis['CatHeart']} You ran out of time! The answer was **{question_data['correct']}**.",
                    color=THEME_COLOR
                )
                
                await interaction.followup.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in trivia game: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
    
    # Help command group
    games_help_group = app_commands.Group(name="games_help", description="Get help with SFlirts mini-games")
    
    @games_help_group.command(name="list", description="Get help with SFlirts mini-games")
    async def help_games(self, interaction: discord.Interaction):
        """Get help with mini-games"""
        try:
            # Get coin emoji
            coin_emoji = emojis["sflirt_coin"]
            
            embed = discord.Embed(
                title=f"{emojis['PurpleHearts']} SFlirts Games Help {emojis['PurpleHearts']}",
                description=f"Play fun mini-games to earn {coin_emoji}! Here are all the available games:",
                color=THEME_COLOR,
                timestamp=datetime.now()
            )
            
            # Gambling games
            embed.add_field(
                name=f"{emojis['sflirt_coin']} Gambling Games",
                value=(
                    f"**`/coinflip [bet] [choice]`** - Bet on heads or tails, win 2x your bet\n"
                    f"**`/slots [bet]`** - Play the slot machine! Various payout multipliers\n"
                    f"**`/roulette [bet] [bet_type] [choice]`** - Bet on colors, numbers, and more!"
                ),
                inline=False
            )
            
            # Dating-themed games
            embed.add_field(
                name=f"{emojis['redglassheart']} Dating Games",
                value=(
                    f"**`/love [user]`** - Test love compatibility with another user\n"
                    f"**`/hangman`** - Play hangman with romance-themed words\n"
                    f"**`/trivia`** - Answer dating and relationship trivia questions\n"
                    f"**`/lovematch`** - Play a memory match game with love symbols"
                ),
                inline=False
            )
            
            # Game rewards info
            embed.add_field(
                name=f"{emojis['Crown']} Game Rewards",
                value=(
                    f"• **Coinflip**: Double your bet if you win\n"
                    f"• **Slots**: Win up to 10x your bet with matching symbols\n"
                    f"• **Roulette**: Bet on numbers (36x), colors or other groups (2x)\n"
                    f"• **Love**: Earn {coin_emoji} based on compatibility percentage\n"
                    f"• **Hangman**: Win {coin_emoji} for correctly guessing the word\n"
                    f"• **Trivia**: Earn {coin_emoji} for correct answers\n"
                    f"• **Love Match**: Win {coin_emoji} by matching all love symbol pairs"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Use /help currency to learn about the {coin_emoji} currency system")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error in help games command: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Games(bot))
