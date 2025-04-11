import discord 
from discord.ext import commands 
import time 
import random 
from utilities import responses, colors
from utilities.database import Database


class ButtonsUI(discord.ui.View):
    def __init__(self, channel_link, bot):
        super().__init__(timeout=None)
        self.db = Database()
        self.bot = bot
        self.add_item(discord.ui.Button(
            label="Back to chat!", 
            url=channel_link, 
            style=discord.ButtonStyle.link
        )) 

        # Add a button with a callback
        self.block_button = discord.ui.Button(
            label="Toggle this notification block",
            style=discord.ButtonStyle.red,
            custom_id="block_notifications"
        )
        self.block_button.callback = self.block_notification  # Set the callback
        self.add_item(self.block_button)
        
    async def update_settings(self, userid, new_value):
        # Check if the user exists
        exists = await self.db.fetchvalue(
            "SELECT 1 FROM user_settings WHERE user_id = ?", 
            (userid,)
        )
        
        if exists:
            # Update existing user
            await self.db.update(
                "user_settings",
                {"dm_notif": new_value},
                "user_id = ?",
                (userid,)
            )
        else:
            # Create new user
            await self.db.insert(
                "user_settings",
                {"user_id": userid, "dm_notif": new_value}
            )

    async def block_notification(self, interaction: discord.Interaction):
        user = interaction.user
        notif_settings = await self.db.fetchvalue(
            "SELECT dm_notif FROM user_settings WHERE user_id = ?",
            (user.id,)
        ) or "enabled"
        
        if notif_settings == "enabled":
            await self.update_settings(user.id, "disabled")
            await interaction.response.send_message("❌ You will no longer receive these notifications.", ephemeral=True)
        else:
            await self.update_settings(user.id, "enabled")
            await interaction.response.send_message("✅ You will receive these notifications.", ephemeral=True)


class Engage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.db = Database()
        # We'll initialize the view in the setup method instead
        self.boring_messages = [
            "hi", "hey", "hello", "yo", "hmm"
        ]
        self.boring_messages_count = {}
        self.last_boring_message_time = {}
        self.delay = 3600
        self.bot.loop.create_task(self.create_table())
   
    async def create_table(self):
        await self.db.create_table("user_settings", """
            user_id INTEGER PRIMARY KEY,
            dm_notif TEXT
        """)
        # Initialize the view after the table is created
        self.bot.add_view(ButtonsUI("", self.bot))
       
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            # check if it's a boring message
            if message.content.lower() not in self.boring_messages:
                return 
            
            user = message.author
            # is notif enabled for that user?
            notif_settings = await self.db.fetchvalue(
                "SELECT dm_notif FROM user_settings WHERE user_id = ?",
                (user.id,)
            ) or "enabled"
            
            if notif_settings == "disabled":
                return 
            
            if user.id in self.boring_messages_count:
                if self.boring_messages_count[user.id] == 3:
                    self.boring_messages_count[user.id] += 1
                    return 
            else:
                self.boring_messages_count[user.id] = 1
                return 
                
            # Check if the message was already sent in the last hour 
            current_time = time.time()
            if user.id in self.last_boring_message_time:
                if (current_time - self.last_boring_message_time[user.id]) < self.delay:
                    return 
                    
            # pick an motivating/engaging message 
            random_message = random.choice(responses).format(msg=message.content)
            # sent it to user
            embed = discord.Embed(title=f"Heyy {user.display_name}", description=random_message, color=colors.primary)
            view = ButtonsUI(f"https://discord.com/channels/{message.guild.id}", self.bot)
            await message.author.send(embed=embed, view=view)
            self.last_boring_message_time[user.id] = current_time
            
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(Engage(bot))