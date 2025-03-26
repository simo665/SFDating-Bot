import discord
from discord.ext import commands
from discord import app_commands
import re
from utilities import colors
from errors.error_logger import error_send
import random 

class MatchSySystems(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
         # Role weight for roles priority 
        self.category_weights = {
            "Gender": {
                "score": 100,
                "roles": {
                    "male": 1350851135501766746,
                    "female": 1350851138139852810,
                }
            },
            "Height Preference": {
                "score": 20,
                "roles": {
                    "taller": 1350851044359278603, 
                    "shorter": 1350851045609181266,
                    "no preference": 1350851047244955770,
                }
            },
            "Age Preference": {
                "score": 20,
                "roles": {
                    "older": 1350851051519086683,
                    "younger": 1350851053587005481,
                    "same age": 1350851055881031884,
                    "no preference": 1350851057814736909,
                }
            },
            "Distance Preference": {
                "score": 16,
                "roles": {
                    "Local": 1350851062302507039,
                    "Long distance": 1350851064286548039,
                }
            },
            "Personality Preference": {
                "score": 12,
                "roles": {
                    "introvert": 1350851082862989463,
                    "extrovert": 1350851086008975422,
                    "optimistic": 1350987464960905226,
                    "ambivert": 1350987302930743401,
                    "realist": 1350987715310518423,
                    "intellectual": 1350851089003450453,
                    "goofy": 1350851091633274921,
                }
            },
            "Hobbies and Interests": { 
                "score": 8,
                "roles": {
                    "gamer": 1350851095173271593,
                    "music": 1350851096746397737,
                    "book": 1350851097828261940,
                    "cooking": 1350851100797964288,
                    "movie": 1350851099510313030,
                    "fitness": 1350851102152589365,
                    "anime": 1350851103876710513,
                }
            },
            "Relationship Status": {
                "score": 24,
                "roles": {
                    "single": 1351001902107725935,
                    "taken": 1351001988644733050,
                    "complicated": 1351002210556842014,
                    "not looking": 1351002077198815362,
                }
            },
            "Dms Status": {
                "score": 48,
                "roles": {
                    "dms open": 1351002346259353621,
                    "dms closed": 1351002452584960083,
                    "dms ask": 1351002555571765280,
                }
            }
        }
        self.age_roles = {
            18: 1350851110021238795,
            19: 1350851112437026876,
            20: 1350851115096473651,
            21: 1350851117000425562,
            22: 1350851119215280139,
            23: 1350851123531218965,
            24: 1350851127897358410,
            25: 1350851131961511957
        }
        self.height_roles = {
            48: 1353905823381848115,
            50: 1353905959491338333,
            52: 1353906092668747857,
            54: 1353906187686383636,
            56: 1353906287871656007,
            58: 1353906388463521832,
            60: 1353906493266854018,
            62: 1353906593175179295,
        }
        self.region = {
            "north America": 1350851068426190920,
            "south america": 1350851076554883072,
            "europe": 1350851070384934934,
            "asia": 1350851072150999235,
            "africa": 1350851074654998529,
            "australia": 1350851078521880586,
        }
        self.personality = {
            "introvert": 1353392254043033651,
            "extrovert": 1353392255309713499,
            "optimist": 1353392259386708020,
            "ambivert": 1353392257465712724,
            "realistic": 1353392260619960371,
            "intellectual": 1353392256459210902,
            "goofy": 1353392261521739849,
        }
        
        # gifs images
        self.love_gifs = [
            "https://media.tenor.com/zIa9q6-d3TQAAAAM/anon-chihaya-bang-dream-it%E2%80%99s-mygo.gif",
            "https://media3.giphy.com/media/Ehw5pKsoHvatq/giphy.gif?cid=6c09b952mqby0av9v3sfh4rkyn03l2bd30h9ffsvf6g8lfot&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=g",
            "https://i.pinimg.com/originals/11/0d/bd/110dbddfd3d662479c214cacb754995d.gif",
            "https://media3.giphy.com/media/13cSgdBHS5keeQ/giphy.gif?cid=6c09b952iq4pecrxq3pvkyweo6zmztkzji3kra0lpjdgj0va&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=g",
        ]
        
    find = app_commands.Group(name="find", description="Find a match commands.") 
    @find.command(name="match", description="Find the best match for you! (In the experimental stage)")
    @app_commands.checks.cooldown(1, 300)
    async def find_match(self, interaction: discord.Interaction):
        try: 
            await interaction.response.defer()
            # Get user information (similar to what you did before)
            user_data = self.extract_user_data(interaction.user)
            for value in user_data:
                if value == None:
                    embed = discord.Embed(name="No completed roles.", description="Our matching system is based on your roles, without complicated roles you cannot find the best match.\n\nGet roles from here: https://discord.com/channels/1349136661971206268/1350840245108871250/1353427439782465687", color=colors.forbidden)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
    
            guild = interaction.guild
            max_score = self.get_max_score()
    
            # Loop through all members in the guild and extract their data
            match_score = None
            best_match = None
    
            for member in guild.members:
                if member.bot:
                    continue
                if member == interaction.user:
                    continue 
                member_data = self.extract_user_data(member)
                for value in member_data:
                    if value == None:
                        continue 
                # Compare user data with each member's data and calculate a match score
                score = self.compare_users(user_data, member_data)
    
                # Check if this member is the best match so far
                if match_score is None or score > match_score and score != match_score:
                    match_score = score
                    best_match = member
                elif score == match_score:
                    best_match = random.choice([best_match, member])
    
            if best_match:
                score_percentage = round((match_score / max_score) * 100, 2)
                member = self.extract_user_data(best_match)
                str_height = str(member['height']) if member['height'] else '' 
                results = [
                    "### <a:PinkHearts:1353727242177478687> Results\n",
                    f"> <a:Heartribbon:1353727310276198494> **Your best match:** {best_match.mention}\n",
                    f"> <a:HeartPopUp:1353727277099126835> **Matching Score:** {match_score}\n",
                    f"> <a:blowingHearts:1353727249354064026> **Percentage:** {score_percentage}%\n",
                    f"### <a:HeartMessage:1353727263933464596> {best_match.display_name}'s Information\n",
                    f"> **Age:** {member['age']} years old.\n" if member.get("age") else "> **Age:** Ask them.\n",
                    f"> **Height:** {str_height[0]}'{str_height[1]}\n" if str_height else "> **Height:** Ask them.\n",
                    f"> **Region:** {member['region']}\n" if member.get("region") else "> **Region:** Ask them.\n",
                    f"> **Personality:** {', '.join(member['personality'])}\n" if member.get("personality") else "> **Personality:** Ask them.\n",
                    f"> **Relationship Status:** {member['relationship_status']}\n" if member.get("relationship_status") else "> **Relationship Status:** Ask them.\n",
                    f"> **DMs Status:** {member['dms_status']}\n" if member.get("dms_status") else "> **DMs Status:** Ask them.\n",
                    f"> **Height Preference:** {member['height_preference']}\n" if member.get("height_preference") else "> **Height Preference:** Ask them.\n",
                    f"> **Age Preference:** {member['age_preference']}\n" if member.get("age_preference") else "> **Age Preference:** Ask them.\n",
                    f"> **Distance Preference:** {member['distance_preference']}\n" if member.get("distance_preference") else "> **Distance Preference:** Ask them.\n",
                    f"> **Personality Preference:** {', '.join(member['personality_preference'])}\n" if member.get("personality_preference") else "> **Personality Preference:** Ask them.\n",
                    f"> **Hobbies:** {', '.join(member['hobbies'])}\n" if member.get("hobbies") else "> **Hobbies:** Ask them.\n",
                    "<:warn:1352035027772375141> Warning!\n> You have to ask them for dms before doing so." if member.get("dms_status") == "dms ask" else ""
                ]
                embed = discord.Embed(
                    title="<a:Heartspin:1353727321508679692> Found a Match!",
                    description="".join(results),
                    color=colors.primary
                )
                embed.add_field(name="Note", value="- The matching system doesn't work randomly. It matches you with the best candidate based on your preferences and roles.\n\n- ❗This command is still in the experimental stage. share your feedback in <#1354071052246061057> channel.")
                embed.set_thumbnail(url=best_match.display_avatar.url)
                embed.set_image(url=random.choice(self.love_gifs))
                await interaction.followup.send(embed=embed)
            else:
                interaction.followup.send("No match found!")
        except Exception:
            await error_send(interaction)
    
    @find_match.error
    async def find_match_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            embed = discord.Embed(title="Wait please!! >_<", description=f"Slow down! Try again in {error.retry_after:.2f} seconds.", color=colors.error)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
    def get_max_score(self):
        max_score = 0
        for value in self.category_weights.values():
            max_score += value["score"]
        return max_score
    
    def extract_user_data(self, user):
        """
        Extract the data for a single user (age, height, preferences, etc.)
        Returns a dictionary with user information.
        """
        user_data = {
            'gender': None,
            'age': None,
            'height': None,
            'region': None,
            'personality': [],
            'relationship_status': None,
            'dms_status': None,
            'height_preference': None,
            'age_preference': None,
            'distance_preference': None,
            'personality_preference': [],
            'hobbies': [],
        }

        for role in user.roles:
            # Fill user_data with the information (similar to what you did before)
            if role.id in self.age_roles.values():
                user_data['age'] = next((key for key, value in self.age_roles.items() if value == role.id), None)
            
            if role.id in self.height_roles.values():
                user_data['height'] = next((key for key, value in self.height_roles.items() if value == role.id), None)
            
            if role.id in self.region.values():
                user_data['region'] = next((key for key, value in self.region.items() if value == role.id), None)
            
            if role.id in self.personality.values():
                user_data['personality'].append(next((key for key, value in self.personality.items() if value == role.id), ""))
            
            if role.id in self.category_weights["Relationship Status"]["roles"].values():
                user_data['relationship_status'] = next((key for key, value in self.category_weights["Relationship Status"]["roles"].items() if value == role.id), None)
            
            if role.id in self.category_weights["Dms Status"]["roles"].values():
                user_data['dms_status'] = next((key for key, value in self.category_weights["Dms Status"]["roles"].items() if value == role.id), None)

            # Preferences data
            if role.id in self.category_weights["Height Preference"]["roles"].values():
                user_data['height_preference'] = next((key for key, value in self.category_weights["Height Preference"]["roles"].items() if value == role.id), None)

            if role.id in self.category_weights["Age Preference"]["roles"].values():
                user_data['age_preference'] = next((key for key, value in self.category_weights["Age Preference"]["roles"].items() if value == role.id), None)

            if role.id in self.category_weights["Distance Preference"]["roles"].values():
                user_data['distance_preference'] = next((key for key, value in self.category_weights["Distance Preference"]["roles"].items() if value == role.id), None)

            if role.id in self.category_weights["Personality Preference"]["roles"].values():
                user_data['personality_preference'].append(next((key for key, value in self.category_weights["Personality Preference"]["roles"].items() if value == role.id), None))
                
            if role.id in self.category_weights["Hobbies and Interests"]["roles"].values():
                user_data['hobbies'].append(next((key for key, value in self.category_weights["Hobbies and Interests"]["roles"].items() if value == role.id), None))
            
            if role.id in self.category_weights["Gender"]["roles"].values():
                user_data['gender'] = next((key for key, value in self.category_weights["Gender"]["roles"].items() if value == role.id), None)
        return user_data

    def compare_users(self, user_data, member_data):
        """
        Compare two users based on their preferences and return a match score.
        """
        score = 0
    
        # Age preference comparison
        if member_data['age'] is not None and user_data['age'] is not None:
            if user_data['age_preference'] == "older" and user_data['age'] < member_data['age']:
                score += self.category_weights["Age Preference"]["score"]
            elif user_data['age_preference'] == "younger" and user_data['age'] > member_data['age']:
                score += self.category_weights["Age Preference"]["score"]
            elif user_data['age_preference'] == "same age" and user_data['age'] == member_data['age']:
                score += self.category_weights["Age Preference"]["score"]
            elif user_data['age_preference'] == "no preference":
                score += self.category_weights["Age Preference"]["score"]
                
        # Height preference comparison
        if member_data['height'] is not None and user_data['height'] is not None:
            if user_data['height_preference'] == "taller" and user_data['height'] < member_data['height']:
                score += self.category_weights["Height Preference"]["score"]
            elif user_data['height_preference'] == "shorter" and user_data['height'] > member_data['height']:
                score += self.category_weights["Height Preference"]["score"]
            elif user_data['height_preference'] == "no preference":
                score += self.category_weights["Height Preference"]["score"]
    
        # Distance preference comparison
        if user_data['distance_preference'] == "Local" and member_data['region'] is not None and user_data['region'] == member_data['region']:
            score += self.category_weights["Distance Preference"]["score"]
        elif user_data['distance_preference'] == "Long distance":
            score += self.category_weights["Distance Preference"]["score"]
    
        # Personality preference comparison
        if member_data['personality'] is not None and user_data['personality_preference'] is not None:
            if set(user_data['personality_preference']).intersection(member_data['personality']):
                score += self.category_weights["Personality Preference"]["score"]
    
        # Hobbies and interests comparison
        if member_data['hobbies'] is not None and user_data['hobbies'] is not None:
            if set(user_data['hobbies']).intersection(member_data['hobbies']):
                score += self.category_weights["Hobbies and Interests"]["score"]
    
        # Relationship status preference comparison
        if member_data['relationship_status'] is not None:
            if member_data['relationship_status'] in ["single", "complicated"] and member_data['relationship_status'] not in ["taken", "not looking"]:
                score += self.category_weights["Relationship Status"]["score"]
    
        # DMs status preference comparison
        if member_data['dms_status'] is not None:
            if member_data['dms_status'] in ["dms open", "dms ask"]:
                score += self.category_weights["Dms Status"]["score"]
    
        if member_data['gender'] is not None:
            if member_data['gender'] != user_data["gender"]:
                score += self.category_weights["Gender"]["score"]
    
        return score


async def setup(bot):
    await bot.add_cog(MatchSySystems(bot))