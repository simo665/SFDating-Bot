import discord 
from discord.ext import commands 
import time 
import random 
from utilities import responses, colors
import sqlite3 


class ButtonsUI(discord.ui.View):
    def __init__(self, channel_link):
        super().__init__(timeout=None)
        self.con = sqlite3.connect("database/data.db")
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
        
    def update_settings(self, userid, new_value):
        cur = self.con.cursor()
        try:
            cur.execute(f"SELECT 1 FROM user_settings WHERE user_id = ?", (userid,))
            exists = cur.fetchone()
            if exists:
                cur.execute(f"UPDATE user_settings SET dm_notif = ? WHERE user_id = ?", (new_value, userid))
            else:
                cur.execute(f"INSERT INTO user_settings (user_id, dm_notif) VALUES (?, ?)", (userid, new_value))
            self.con.commit()
        finally:
            cur.close()

    async def block_notification(self, interaction: discord.Interaction):
        cur = self.con.cursor()
        current_setting = ""
        user = interaction.user
        try:
            cur.execute("SELECT dm_notif FROM user_settings WHERE user_id = ?", (user.id,))
            result = cur.fetchone()
            notif_settings = result[0] if result else "enabled"
        finally:
            cur.close()
        
        if notif_settings == "enabled":
            self.update_settings(user.id, "disabled")
            await interaction.response.send_message("❌ You will no longer receive these notifications.", ephemeral=True)
        else:
            self.update_settings(user.id, "enabled")
            await interaction.response.send_message("✅ You will receive these notifications.", ephemeral=True)


class Engage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        bot.add_view(ButtonsUI(""))
        self.boring_messages = [
            "hi", "hey", "hello", "yo", "hmm"
        ]
        self.boring_messages_count = {}
        self.last_boring_message_time = {}
        self.delay = 3600
        self.con = sqlite3.connect("database/data.db")
        self.create_table()
   
    def create_table(self):
        cur = self.con.cursor()
        try:
            cur.execute("""CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                dm_notif TEXT
            )""")
            self.con.commit()
        finally:
            cur.close()
       
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            # check if it's a boring message
            if message.content not in self.boring_messages:
                return 
            
            user = message.author
            # is notif enabled for that user?
            notif_settings = "enabled"
            cur = self.con.cursor()
            try:
                cur.execute("SELECT dm_notif FROM user_settings WHERE user_id = ?", (user.id,))
                result = cur.fetchone()
                notif_settings = result[0] if result else "enabled"
                self.con.commit()
            finally:
                cur.close()
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
            view = ButtonsUI(f"https://discord.com/channels/{message.guild.id}")
            await message.author.send(embed=embed, view=view)
            self.last_boring_message_time[user.id] = current_time
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(Engage(bot))