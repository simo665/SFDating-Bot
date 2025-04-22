import json

def load_roles_ids(category: str, guild_id, file_path: str = "./configs/roles/RolesID.json") -> dict:
    guild_id = str(guild_id)
    with open(file_path, "r") as f:
        data = json.load(f)

    guild_data = data.get(guild_id)
    if not guild_data:
        return {}

    return guild_data.get(category, {})