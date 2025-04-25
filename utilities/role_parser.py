import json
import logging
import discord
import config

logger = logging.getLogger("./errors/errors.log")

class RoleParser:
    def __init__(self):
        self.roles_data = {}
        self.guild_roles = {}
        self.category_weights = {
            "Gender": {"score": 0, "roles": {}},
            "Height Preference": {"score": 20, "roles": {}},
            "Age Preference": {"score": 20, "roles": {}},
            "Distance Preference": {"score": 16, "roles": {}},
            "Personality Preference": {"score": 3, "roles": {}},
            "Hobbies and Interests": {"score": 2, "roles": {}},
            "Relationship Status": {"score": 24, "roles": {}},
            "Dms Status": {"score": 48, "roles": {}}
        }
        self.age_roles = {}
        self.height_roles = {}
        self.region = {}
        self.personality = {}
        self.sexuality = {}
        self.verified_roles = {}
        self.exclusion_roles = []
        self.required_roles = {}
        
        # Load roles data
        self.load_roles()
        
    def load_roles(self):
        try:
            with open(config.ROLES_CONFIG_PATH, "r") as f:
                self.roles_data = json.load(f)
            logger.info("Successfully loaded roles configuration")
        except FileNotFoundError:
            logger.error(f"Roles configuration file not found at {config.ROLES_CONFIG_PATH}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON in roles configuration file")
        except Exception as e:
            logger.error(f"Error loading roles configuration: {e}")
    
    def parse_guild_roles(self, guild):
        """Parse roles for a specific guild"""
        guild_id = str(guild.id)
        
        if guild_id not in self.roles_data:
            logger.warning(f"No role configuration found for guild ID {guild_id}")
            return False
        
        guild_roles = self.roles_data[guild_id]
        
        # Gender roles
        self.category_weights["Gender"]["roles"]["male"] = guild_roles.get("gender_roles", {}).get("male")
        self.category_weights["Gender"]["roles"]["female"] = guild_roles.get("gender_roles", {}).get("female")
        self.category_weights["Gender"]["roles"]["transmale"] = guild_roles.get("gender_roles", {}).get("transmale")
        self.category_weights["Gender"]["roles"]["transfemale"] = guild_roles.get("gender_roles", {}).get("transfemale")
        self.category_weights["Gender"]["roles"]["none"] = guild_roles.get("gender_roles", {}).get("none")
        
        # Height preference
        self.category_weights["Height Preference"]["roles"] = guild_roles.get("height_preference", {})
        
        # Age preference
        self.category_weights["Age Preference"]["roles"] = guild_roles.get("age_preference", {})
        
        # Distance preference
        self.category_weights["Distance Preference"]["roles"] = guild_roles.get("distance", {})
        
        # Personality preference
        self.category_weights["Personality Preference"]["roles"] = guild_roles.get("partner_personality", {})
        
        # Hobbies and interests
        self.category_weights["Hobbies and Interests"]["roles"] = guild_roles.get("hobbies", {})
        
        # Relationship status
        self.category_weights["Relationship Status"]["roles"] = guild_roles.get("relationship_status", {})
        
        # DMs status
        self.category_weights["Dms Status"]["roles"] = guild_roles.get("dms_status", {})
        
        # Age roles
        self.age_roles = guild_roles.get("age", {})
        
        # Height roles
        self.height_roles = guild_roles.get("height", {})
        
        # Region
        self.region = guild_roles.get("region", {})
        
        # Personality
        self.personality = guild_roles.get("personality", {})
        
        # Sexuality
        self.sexuality = guild_roles.get("sexuality", {})
        
        # Verified roles
        self.verified_roles = guild_roles.get("verified_roles", {})
        
        # Collect exclusion roles
        exclusion_role_ids = []
        relationship_status = guild_roles.get("relationship_status", {})
        dms_status = guild_roles.get("dms_status", {})
        
        # Add relationship status roles that disqualify from matching
        for status_type in config.EXCLUSION_ROLE_TYPES:
            if status_type in relationship_status:
                exclusion_role_ids.append(relationship_status[status_type])
        
        # Add DMs closed status role
        if "dms closed" in dms_status:
            exclusion_role_ids.append(dms_status["dms closed"])
            
        self.exclusion_roles = exclusion_role_ids
        
        # Save required role categories
        self.required_roles = {
            category: guild_roles.get(category, {})
            for category in config.REQUIRED_ROLE_CATEGORIES
        }
        
        # Cache the parsed roles data for this guild
        self.guild_roles[guild_id] = {
            "category_weights": self.category_weights,
            "age_roles": self.age_roles,
            "height_roles": self.height_roles,
            "region": self.region,
            "personality": self.personality,
            "sexuality": self.sexuality,
            "verified_roles": self.verified_roles,
            "exclusion_roles": self.exclusion_roles,
            "required_roles": self.required_roles
        }
        
        logger.info(f"Successfully parsed roles for guild ID {guild_id}")
        return True
    
    def get_guild_roles(self, guild):
        """Get parsed roles for a guild, parsing if necessary"""
        guild_id = str(guild.id)
        
        if guild_id not in self.guild_roles:
            if not self.parse_guild_roles(guild):
                return None
        
        return self.guild_roles[guild_id]
    
    def extract_user_data(self, member):
        """Extract user data from member roles"""
        guild_roles = self.get_guild_roles(member.guild)
        if not guild_roles:
            return None
        
        user_data = {
            "gender": None,
            "age": None,
            "height": None,
            "region": None,
            "personality": [],
            "relationship_status": None,
            "dms_status": None,
            "height_preference": None,
            "age_preference": None,
            "distance_preference": None,
            "personality_preference": [],
            "hobbies": [],
            "sexuality": None,
            "exclusion_roles": []
        }
        
        member_role_ids = [role.id for role in member.roles]
        
        # Check gender roles
        gender_roles = guild_roles["category_weights"]["Gender"]["roles"]
        for gender, role_id in gender_roles.items():
            if role_id in member_role_ids:
                user_data["gender"] = gender
                break
        
        # Check age roles
        for age, role_id in guild_roles["age_roles"].items():
            if role_id in member_role_ids:
                # Extract numeric age from role name (e.g., "age18" -> 18)
                if age.startswith("age"):
                    user_data["age"] = int(age[3:])
                break
        
        # Check height roles
        for height, role_id in guild_roles["height_roles"].items():
            if role_id in member_role_ids:
                user_data["height"] = height
                break
        
        # Check region
        for region, role_id in guild_roles["region"].items():
            if role_id in member_role_ids:
                user_data["region"] = region
                break
        
        # Check personality traits
        for trait, role_id in guild_roles["personality"].items():
            if role_id in member_role_ids:
                user_data["personality"].append(trait)
        
        # Check relationship status
        for status, role_id in guild_roles["category_weights"]["Relationship Status"]["roles"].items():
            if role_id in member_role_ids:
                user_data["relationship_status"] = status
                break
        
        # Check DMs status
        for status, role_id in guild_roles["category_weights"]["Dms Status"]["roles"].items():
            if role_id in member_role_ids:
                user_data["dms_status"] = status
                break
        
        # Check height preference
        for pref, role_id in guild_roles["category_weights"]["Height Preference"]["roles"].items():
            if role_id in member_role_ids:
                user_data["height_preference"] = pref
                break
        
        # Check age preference
        for pref, role_id in guild_roles["category_weights"]["Age Preference"]["roles"].items():
            if role_id in member_role_ids:
                user_data["age_preference"] = pref
                break
        
        # Check distance preference
        for pref, role_id in guild_roles["category_weights"]["Distance Preference"]["roles"].items():
            if role_id in member_role_ids:
                user_data["distance_preference"] = pref
                break
        
        # Check personality preference
        for trait, role_id in guild_roles["category_weights"]["Personality Preference"]["roles"].items():
            if role_id in member_role_ids:
                user_data["personality_preference"].append(trait)
        
        # Check hobbies
        for hobby, role_id in guild_roles["category_weights"]["Hobbies and Interests"]["roles"].items():
            if role_id in member_role_ids:
                user_data["hobbies"].append(hobby)
        
        # Check sexuality
        for sexuality, role_id in guild_roles["sexuality"].items():
            if role_id in member_role_ids:
                user_data["sexuality"] = sexuality
                break
        
        # Check for exclusion roles
        for role_id in guild_roles["exclusion_roles"]:
            if role_id in member_role_ids:
                user_data["exclusion_roles"].append(role_id)
        
        return user_data
    
    def check_required_roles(self, member):
        """Check if the member has all required roles"""
        guild_roles = self.get_guild_roles(member.guild)
        if not guild_roles:
            return False, "Guild roles not configured"
        
        member_role_ids = [role.id for role in member.roles]
        missing_categories = []
        
        # Check required role categories
        for category, roles in guild_roles["required_roles"].items():
            has_role_in_category = False
            for role_id in roles.values():
                if role_id in member_role_ids:
                    has_role_in_category = True
                    break
            
            if not has_role_in_category:
                missing_categories.append(category)
        
        if missing_categories:
            missing_str = ", ".join(missing_categories).replace("_", " ")
            return False, f"Missing roles from these categories: {missing_str}"
        
        return True, None
    
    def get_max_score(self):
        """Calculate maximum possible score for matching"""
        # More realistic max score calculation that considers what's actually
        # achievable in a real match scenario
        total = 0
        
        # Add Gender score
        total += self.category_weights["Gender"]["score"]
        
        # Add Height Preference score
        total += self.category_weights["Height Preference"]["score"]
        
        # Add Age Preference score
        total += self.category_weights["Age Preference"]["score"]
        
        # Add Distance Preference score
        total += self.category_weights["Distance Preference"]["score"]
        
        # Add Personality Preference score (not multiplied by all possible personality types)
        total += self.category_weights["Personality Preference"]["score"]
        
        # Add Hobbies score (not multiplied by all possible hobbies)
        total += self.category_weights["Hobbies and Interests"]["score"]
        
        # Add Relationship Status score
        total += self.category_weights["Relationship Status"]["score"]
        
        # Add DMs Status score
        total += self.category_weights["Dms Status"]["score"]
        
        return total
    
    def compare_users(self, user1_data, user2_data):
        """Compare two users and calculate a match score"""
        if not user1_data or not user2_data:
            return 0
        
        score = 0
        
        # Gender matching logic based on sexuality
        if user1_data["gender"] and user2_data["gender"]:
            # Simple gender matching for now, can be expanded with sexuality
            if user1_data["gender"] != user2_data["gender"]:
                score += self.category_weights["Gender"]["score"]
        
        # Height preference matching
        if user1_data["height_preference"] and user2_data["height"]:
            if user1_data["height_preference"] == "taller" and float(user2_data["height"]) >= float(user1_data["height"]):
                score += self.category_weights["Height Preference"]["score"]
            elif user1_data["height_preference"] == "shorter" and float(user2_data["height"]) <= float(user1_data["height"]):
                score += self.category_weights["Height Preference"]["score"]
            elif user1_data["height_preference"] == "no preference":
                score += self.category_weights["Height Preference"]["score"]
        
        # Age preference matching
        if user1_data["age_preference"] and user2_data["age"]:
            if user1_data["age_preference"] == "older" and user2_data["age"] > user1_data["age"]:
                score += self.category_weights["Age Preference"]["score"]
            elif user1_data["age_preference"] == "younger" and user2_data["age"] < user1_data["age"]:
                score += self.category_weights["Age Preference"]["score"]
            elif user1_data["age_preference"] == "same age" and user2_data["age"] == user1_data["age"]:
                score += self.category_weights["Age Preference"]["score"]
            elif user1_data["age_preference"] == "no preference":
                score += self.category_weights["Age Preference"]["score"]
        
        # Distance preference matching
        if user1_data["distance_preference"] and user2_data["region"]:
            if user1_data["distance_preference"] == "Long distance":
                score += self.category_weights["Distance Preference"]["score"]
            elif user1_data["distance_preference"] == "Local" and user1_data["region"] == user2_data["region"]:
                score += self.category_weights["Distance Preference"]["score"]
            elif user1_data["distance_preference"] == "none":
                score += self.category_weights["Distance Preference"]["score"]
        
        # Personality preference matching
        common_personality_traits = 0
        for trait in user1_data["personality_preference"]:
            if trait in user2_data["personality"]:
                common_personality_traits += 1
        
        if common_personality_traits > 0:
            # Award points proportional to how many personality traits match
            score += self.category_weights["Personality Preference"]["score"] * (common_personality_traits / max(1, len(user1_data["personality_preference"])))
        
        # Hobbies matching
        common_hobbies = 0
        for hobby in user1_data["hobbies"]:
            if hobby in user2_data["hobbies"]:
                common_hobbies += 1
        
        if common_hobbies > 0:
            # Award points proportional to how many hobbies match
            score += self.category_weights["Hobbies and Interests"]["score"] * (common_hobbies / max(1, len(user1_data["hobbies"])))
        
        # Relationship status matching - both should be compatible (looking, single)
        compatible_statuses = ["single", "looking", "figuring_out"]
        if user1_data["relationship_status"] in compatible_statuses and user2_data["relationship_status"] in compatible_statuses:
            score += self.category_weights["Relationship Status"]["score"]
        
        # DMs status - must be open or ask to match
        if user2_data["dms_status"] in ["dms open", "dms ask"]:
            score += self.category_weights["Dms Status"]["score"]
        
        return score
        