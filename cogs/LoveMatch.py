import discord
from discord import app_commands
from discord.ext import commands
import random
from typing import Dict, List
import logging
import asyncio
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.db_manager import DatabaseManager
from utilities.variables import get_emojis_variables

logger = logging.getLogger('bot.love_match')

class LoveMatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.active_games = {}
        self.games_on_cooldown = {}
        
        # Get custom emojis
        self.emojis = get_emojis_variables()
        
        # Define the main theme color (red)
        self.THEME_COLOR = discord.Color.from_str("#c40000")
        
        # Game settings
        self.WIN_REWARD = 100  # SFlirts awarded for winning
        self.LOSS_PENALTY = 25  # SFlirts deducted for losing
        self.grid_size = 4  # 4x4 grid
        self.max_attempts = 10  # Number of failed matches allowed
        self.cooldown_seconds = 300  # 5 minutes cooldown
        
        # Love symbols for matching
        self.love_symbols = [
            self.emojis["redglassheart"],
            self.emojis["PinkHearts"], 
            self.emojis["Heartspin"], 
            self.emojis["TwoHearts"],
            self.emojis["HeartMessage"],
            self.emojis["CatHeart"],
            self.emojis["LikeHeart"],
            self.emojis["blowingHearts"]
        ]
    
    async def check_cooldown(self, user_id, cooldown_seconds=300):
        """Check if a user is on cooldown for the game"""
        key = f"{user_id}_love_match"
        
        if key in self.games_on_cooldown:
            cooldown_end = self.games_on_cooldown[key]
            if datetime.now() < cooldown_end:
                time_left = cooldown_end - datetime.now()
                return False, int(time_left.total_seconds())
        
        # Set cooldown
        self.games_on_cooldown[key] = datetime.now() + timedelta(seconds=cooldown_seconds)
        return True, 0
    
    def create_love_grid(self):
        """Create a grid of love symbols for the memory game"""
        # Take 8 symbols for a 4x4 grid (8 pairs)
        symbols = self.love_symbols.copy()
        random.shuffle(symbols)
        symbols = symbols[:8] * 2  # Create pairs
        random.shuffle(symbols)
        
        # Create the 4x4 grid
        grid = []
        for i in range(0, len(symbols), self.grid_size):
            grid.append(symbols[i:i+self.grid_size])
        return grid
    
    def display_grid(self, user_id):
        """Format the current game grid for display"""
        game = self.active_games[user_id]
        
        column_headers = "   " + "  ".join([f"  {i+1}  " for i in range(self.grid_size)])
        rows = [column_headers]
        
        for i, row in enumerate(game["display"]):
            row_display = f"{i+1}  " + "  ".join(row)
            rows.append(row_display)
            
        return "\n".join(rows)

    @app_commands.command(name="lovematch", description="💕 Play a love-themed memory match game to earn SFlirts!")
    async def love_match(self, interaction: discord.Interaction):
        """Start a love-themed memory matching game"""
        try:
            # Check if user already has an active game
            if interaction.user.id in self.active_games:
                embed = discord.Embed(
                    title=f"{self.emojis['offline']} Game Already in Progress",
                    description=f"You already have an active Love Match game! Use /reveal to continue playing.",
                    color=self.THEME_COLOR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Check cooldown
            can_play, seconds_left = await self.check_cooldown(interaction.user.id, self.cooldown_seconds)
            if not can_play:
                embed = discord.Embed(
                    title=f"{self.emojis['offline']} Game on Cooldown",
                    description=f"You need to wait {seconds_left} seconds before starting a new Love Match game.",
                    color=self.THEME_COLOR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            # Create a new game
            grid = self.create_love_grid()
            
            # Create a hidden grid with card backs
            hidden_grid = [["🎴" for _ in range(self.grid_size)] for _ in range(self.grid_size)]
            
            # Initialize game state
            self.active_games[interaction.user.id] = {
                "grid": grid,
                "display": hidden_grid,
                "first_guess": None,
                "matches_found": 0,
                "attempts": 0
            }
            
            # Create the game embed
            embed = discord.Embed(
                title=f"{self.emojis['PinkHearts']} Love Match Memory Game {self.emojis['PinkHearts']}",
                description=(
                    f"**{interaction.user.mention}** is playing Love Match!\n\n"
                    f"Find all the matching love symbols to win {self.WIN_REWARD} {self.emojis['sflirt_coin']}!\n"
                    f"You have **{self.max_attempts}** failed attempts before losing {self.LOSS_PENALTY} {self.emojis['sflirt_coin']}.\n\n"
                    f"\n{self.display_grid(interaction.user.id)}\n\n"
                    f"Use **/reveal row column** to flip a card! (Example: /reveal 2 3)"
                ),
                color=self.THEME_COLOR,
                timestamp=datetime.now()
            )
            
            embed.set_footer(text="💕 Match all symbols to win! 💕")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in love_match command: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    
    @app_commands.command(name="reveal", description="🎴 Reveal a card in your Love Match game")
    async def reveal(self, interaction: discord.Interaction, row: int, column: int):
        """Reveal a card in the Love Match game"""
        try:
            # Check if user has an active game
            if interaction.user.id not in self.active_games:
                embed = discord.Embed(
                    title=f"{self.emojis['offline']} No Active Game",
                    description="You don't have an active Love Match game! Start one with /lovematch",
                    color=self.THEME_COLOR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            game = self.active_games[interaction.user.id]
            
            # Validate row and column
            if not (1 <= row <= self.grid_size and 1 <= column <= self.grid_size):
                embed = discord.Embed(
                    title=f"{self.emojis['offline']} Invalid Position",
                    description=f"Please enter valid positions between 1 and {self.grid_size}.",
                    color=self.THEME_COLOR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Adjust for 0-based indexing
            row -= 1
            column -= 1
            
            # Check if the card is already revealed
            if game["display"][row][column] != "🎴":
                embed = discord.Embed(
                    title=f"{self.emojis['offline']} Card Already Revealed",
                    description="This card is already revealed! Choose another one.",
                    color=self.THEME_COLOR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Reveal the card
            actual_symbol = game["grid"][row][column]
            game["display"][row][column] = actual_symbol
            
            embed = discord.Embed(
                color=self.THEME_COLOR,
                timestamp=datetime.now()
            )
            
            # First or second card of the pair
            if game["first_guess"] is None:
                # First card of the pair
                game["first_guess"] = (row, column)
                embed.title = f"{self.emojis['HeartMessage']} First Card Revealed!"
                embed.description = (
                    f"You revealed {actual_symbol} at position ({row+1}, {column+1}).\n"
                    f"Now choose another card to try to match it!\n\n"
                    f"\n{self.display_grid(interaction.user.id)}\n"
                )
                await interaction.response.send_message(embed=embed)
            else:
                # Second card of the pair
                first_row, first_col = game["first_guess"]
                first_symbol = game["grid"][first_row][first_col]
                
                # Check if it's a match
                if actual_symbol == first_symbol:
                    # Match found!
                    game["matches_found"] += 1
                    game["first_guess"] = None
                    
                    embed.title = f"{self.emojis['PinkHearts']} Match Found! {self.emojis['PinkHearts']}"
                    embed.description = (
                        f"You found a match! {actual_symbol} pairs with {first_symbol}!\n"
                        f"Matches found: **{game['matches_found']}/8**\n"
                        f"Failed attempts: **{game['attempts']}/{self.max_attempts}**\n\n"
                        f"\n{self.display_grid(interaction.user.id)}\n"
                    )
                    embed.color = discord.Color.green()
                    
                    # Check if all matches found
                    if game["matches_found"] >= 8:
                        # Player wins!
                        self.db.record_game_win(interaction.user.id, self.WIN_REWARD)
                        
                        win_embed = discord.Embed(
                            title=f"{self.emojis['Crown']} Love Match Victory! {self.emojis['Crown']}",
                            description=(
                                f"Congratulations {interaction.user.mention}!\n\n"
                                f"You found all **8 pairs** of love symbols with only **{game['attempts']}** failed attempts!\n"
                                f"Your heart-finding skills are impressive! {self.emojis['blowingHearts']}\n\n"
                                f"You've earned **{self.WIN_REWARD}** {self.emojis['sflirt_coin']} for your victory!"
                            ),
                            color=discord.Color.gold(),
                            timestamp=datetime.now()
                        )
                        
                        # Delete the game
                        del self.active_games[interaction.user.id]
                        await interaction.response.send_message(embed=win_embed)
                    else:
                        await interaction.response.send_message(embed=embed)
                else:
                    # Not a match
                    game["attempts"] += 1
                    game["first_guess"] = None
                    
                    embed.title = f"{self.emojis['BlackCatHeart']} Not a Match! {self.emojis['BlackCatHeart']}"
                    embed.description = (
                        f"No match! {first_symbol} ≠ {actual_symbol}\n"
                        f"Matches found: **{game['matches_found']}/8**\n"
                        f"Failed attempts: **{game['attempts']}/{self.max_attempts}**\n\n"
                        f"\n{self.display_grid(interaction.user.id)}\n"
                    )
                    embed.color = discord.Color.red()
                    
                    # Show the mismatch briefly, then hide the cards again
                    await interaction.response.send_message(embed=embed)
                    await asyncio.sleep(2)
                    
                    # Hide the cards again
                    game["display"][row][column] = "🎴"
                    game["display"][first_row][first_col] = "🎴"
                    
                    # Update the embed to show hidden cards
                    embed.description = (
                        f"No match! {first_symbol} ≠ {actual_symbol}\n"
                        f"Matches found: **{game['matches_found']}/8**\n"
                        f"Failed attempts: **{game['attempts']}/{self.max_attempts}**\n\n"
                        f"\n{self.display_grid(interaction.user.id)}\n"
                    )
                    
                    # Check if player has lost
                    if game["attempts"] >= self.max_attempts:
                        # Player loses
                        self.db.record_game_loss(interaction.user.id, self.LOSS_PENALTY)
                        
                        loss_embed = discord.Embed(
                            title=f"{self.emojis['offline']} Game Over! {self.emojis['offline']}",
                            description=(
                                f"Sorry {interaction.user.mention}, you've run out of attempts!\n\n"
                                f"You found **{game['matches_found']}** out of 8 pairs.\n"
                                f"Better luck next time! {self.emojis['LikeHeart']}\n\n"
                                f"You've lost **{self.LOSS_PENALTY}** {self.emojis['sflirt_coin']} for this game."
                            ),
                            color=self.THEME_COLOR,
                            timestamp=datetime.now()
                        )
                        
                        # Delete the game
                        del self.active_games[interaction.user.id]
                        await interaction.edit_original_response(embed=loss_embed)
                    else:
                        await interaction.edit_original_response(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in reveal command: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="endmatch", description="⚠️ End your current Love Match game early")
    async def end_match(self, interaction: discord.Interaction):
        """End the current Love Match game early"""
        try:
            if interaction.user.id not in self.active_games:
                embed = discord.Embed(
                    title=f"{self.emojis['offline']} No Active Game",
                    description="You don't have an active Love Match game to end!",
                    color=self.THEME_COLOR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Delete the game
            del self.active_games[interaction.user.id]
            
            embed = discord.Embed(
                title=f"{self.emojis['BlackCatHeart']} Game Ended",
                description=(
                    f"Your Love Match game has been ended.\n"
                    f"No {self.emojis['sflirt_coin']} were gained or lost.\n"
                    f"Start a new game with /lovematch when you're ready!"
                ),
                color=self.THEME_COLOR,
                timestamp=datetime.now()
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in end_match command: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            
async def setup(bot):
    await bot.add_cog(LoveMatch(bot))