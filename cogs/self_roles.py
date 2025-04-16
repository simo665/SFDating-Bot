import discord 
from discord.ext import commands 
from discord import app_commands
from utilities import get_message_from_template
from errors.error_logger import error_send
from utilities.variables import get_emojis_variables
import time
from utilities import colors
from datetime import timedelta


class RolesLinkView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label=f"Grab Roles", 
            url="https://discord.com/channels/1349136661971206268/1350840245108871250/1359905464762110197", 
            style=discord.ButtonStyle.link,
            emoji=discord.PartialEmoji(name="PinkHearts", id=1359829058942144594, animated=True)
        ))


class SelfRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        
        # Roles reminder 
        self.last_remind = {}
        self.warns = {}
    
    self_group = app_commands.Group(name="self", description="Self related commands")
    roles_group = app_commands.Group(name="roles", description="roles related commands", parent=self_group)
    
    @roles_group.command(name="setup", description="setup self roles automatically")
    async def setuproles(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        try:
            await interaction.response.send_message("Ok!", ephemeral=True)
            templates = [
                "selfroles_age", "selfroles_gender", "selfroles_sexuality", "selfroles_region", "selfroles_occupation", "selfroles_relationship", "selfroles_dms",
                "selfroles_age_preference", "selfroles_height", "selfroles_height_preference", "selfroles_distance", "selfroles_personality",
                "selfroles_personality_preference", "selfroles_hobbies", "selfroles_colors",
            ]
            channel = channel if channel else interaction.channel
            
            for template in templates:
                message_data = get_message_from_template(template)
                await channel.send(message_data["content"], embeds=message_data["embeds"], view=message_data["view"])
                #await asyncio.sleep(1)
            
        except Exception:
            await error_send(interaction)
            
            
    # roles reminder 
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message.author.bot:
                return 
            user = message.author
            # add delay 
            current_time = time.time()
            if user.id not in self.last_remind:
                self.last_remind[user.id] = 0
                
            if current_time - self.last_remind[user.id] < 45:
                return 
            
            age_roles_ids = {
                "age18": 1350851110021238795,
                "age19": 1350851112437026876,
                "age20": 1350851115096473651,
                "age21": 1350851117000425562,
                "age22": 1350851119215280139,
                "age23": 1350851123531218965,
                "age24": 1350851127897358410,
                "age25": 1350851131961511957
            }
            gender_roles_ids = {
                "male": 1350851135501766746,
                "female": 1350851138139852810,
                "transmale": 1359888608508510430,
                "transfemale": 1359888703211704431,
                "none": 1359888867750318160
            }
           
            
            emojis = get_emojis_variables()
            
            has_age_role = False
            has_gender_role = False
            # check roles
            for role in user.roles:
                # check age role
                if role.id in age_roles_ids.values():
                    has_age_role = True
                # check gender role 
                if role.id in gender_roles_ids.values():
                    has_gender_role = True 
             
            if has_gender_role == False or has_gender_role == False:
                if user.id not in self.warns:
                    self.warns[user.id] = 1
                reply_messages = {
                    1: f"{user.mention}, grab your roles using the button below. Age/Gender roles are required.",
                    2: f"{user.mention}, please grab your roles below. This is your second warning. You may get muted.",
                    3: f"{user.mention}, you’ve been muted for not picking roles. Get them after unmute from: <#1350840245108871250>."
                }
                colors_ = {
                    1: colors.forbidden,
                    2: 0xe38c04,
                    3: colors.red
                }
                notif_embed = discord.Embed(
                    title=f"{emojis.get('emoji_warn')} Rquire roles!",
                    description=reply_messages[self.warns[user.id]],
                    color=colors_[self.warns[user.id]]
                )
                view = RolesLinkView()
                try: 
                    await message.reply(embed=notif_embed, delete_after=12, view=view)
                except discord.HTTPException:
                    await message.channel.send(content=user.mention, embed=notif_embed, delete_after=12, view=view)
                    
                if self.warns[user.id] == 3:
                    try:
                        await user.timeout(timedelta(minutes=2), reason="Muted for not getting the roles.")
                    except discord.Forbidden:
                        pass
                
                self.warns[user.id] += 1
                self.last_remind[user.id] = time.time()
         
        except Exception:
            await error_send()
        
async def setup(bot):
    await bot.add_cog(SelfRoles(bot))