import discord 
from discord import app_commands
from discord.ext import commands 
from utilities import colors
from errors.error_logger import error_send
from utilities import send_log, get_all_variables


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        
    # role auto moderation 
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        try:
            # auto kick minors 
            minors_role_id = 1359938581992444164
            minors_role = discord.utils.get(before.guild.roles, id=minors_role_id)
            
            if minors_role in after.roles:
                kick_message = discord.Embed(
                    title="Minor Kicked",
                    description="We really apologize for kicking you out, but for minors safety we do not accept minors in our dating server.\n\nHowever, You can join our friendly server for both minors and adults. (Not a dating server)\nLink: https://discord.gg/eAhGqfkSv7\n\nYou are not Underage? Appeal your punishment from this link: https://appeal.gg/s/1349136661971206268",
                    color=colors.primary 
                )
                kick_message.set_footer(text="SFDating Safety.")
                kick_message.set_image(url="https://raw.githubusercontent.com/simo665/SFD-Assets/refs/heads/main/images/SFDatingSupport.jpg")
                try:
                    await after.send(embed=kick_message)
                except Exception:
                    pass
                await after.ban(reason="Automod: Minor")
                
                
                # logging 
                variables = get_all_variables(after, after.guild, after)
                variables.update({"reason": "Underage"})
                await send_log(self.bot, variables, "log_underage")
                
        except Exception:
            await error_send() 
            
async def setup(bot):
    await bot.add_cog(AutoMod(bot))