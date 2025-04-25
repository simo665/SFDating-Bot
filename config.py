# Bot configuration settings

# Command cooldown in seconds (6 hours = 21600 seconds)
MATCH_COMMAND_COOLDOWN = 21600 

# Match threshold (minimum required points for a viable match)
MIN_MATCH_THRESHOLD = 25

# Channels where the match command can be used (customize these IDs)
MATCH_COMMAND_CHANNELS = [
    1354185377371525271,  # match-making channel 
    1354861828047503461,  # dating-app channel
    1364349599602442300   # find-match channel
]

# JSON file path for roles configuration
ROLES_CONFIG_PATH = "./configs/roles/RolesID.json"

# Database file path
DATABASE_PATH = "./database/matchmaking.db"

# Match acceptance timeout (in seconds) - 24 hours
MATCH_ACCEPTANCE_TIMEOUT = 86400

# Number of days to exclude declined matches from appearing again
DECLINED_MATCHES_EXCLUSION_DAYS = 7

# Exclusion roles - users with these roles won't be suggested as matches
EXCLUSION_ROLE_TYPES = [
    "taken",
    "not_looking",
    "friends_only"
]

# Required role category groups - users must have at least one role from each category
REQUIRED_ROLE_CATEGORIES = [
    "gender_roles",
    "age",
    "region"
]

# Verification role IDs
VERIFIED_ROLES_ID = [1350898361032642641, 1350898277813583932]

# Love GIFs for match messages
LOVE_GIFS = [
    "https://media.tenor.com/zIa9q6-d3TQAAAAM/anon-chihaya-bang-dream-it%E2%80%99s-mygo.gif",
    "https://media3.giphy.com/media/Ehw5pKsoHvatq/giphy.gif?cid=6c09b952mqby0av9v3sfh4rkyn03l2bd30h9ffsvf6g8lfot&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=g",
    "https://i.pinimg.com/originals/11/0d/bd/110dbddfd3d662479c214cacb754995d.gif",
    "https://media3.giphy.com/media/13cSgdBHS5keeQ/giphy.gif?cid=6c09b952iq4pecrxq3pvkyweo6zmztkzji3kra0lpjdgj0va&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=g",
]

# Colors for embeds
class Colors:
    SUCCESS = 0x57F287  # Green
    ERROR = 0xED4245    # Red
    WARNING = 0xFEE75C  # Yellow
    INFO = 0x5865F2     # Blurple
    LOVE = 0xFF69B4     # Pink
    SECONDARY = 0x2F3136  # Discord dark theme background

# Channel IDs for important channels
ROLES_CHANNEL_ID = 1364365504378044528
ROLES_CHANNEL_LINK = "https://discord.com/channels/1364310690046939197/1364365504378044528"
