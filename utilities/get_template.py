import discord
from datetime import datetime
import time
from utilities.components_callback import DropDownSelect, CustomButton 
import os
import json
from utilities.colors import *


class PersistentView(discord.ui.View):
    def __init__(self, components_data):
        super().__init__(timeout=None)
        self.add_components(components_data)

    def add_components(self, components_data):
        for action_row in components_data:
            if action_row.get('type') == 1:  # ActionRow component
                for component in action_row.get('components', []):
                    self.add_item(self.create_component(component))


    def create_component(self, component_data):
        component_type = component_data.get('type')
        
        if component_type == 2:  # Button
            emoji_data = component_data.get('emoji')
            emoji = None
            if emoji_data:
                emoji = discord.PartialEmoji(
                    id=emoji_data.get('id', None),
                    name=emoji_data['name'],
                    animated=emoji_data.get('animated', False)
                )
               
            return CustomButton(
                custom_id=component_data.get('custom_id'),
                label=component_data.get('label'),
                style=component_data.get('style', 1),  # Default to primary style
                emoji=emoji,
                url=component_data.get('url', "") if component_data.get('style') == 5 else None
            )
            
        elif component_type == 3:  # Select menu
            options = [
                discord.SelectOption(
                    label=opt.get('label'),
                    value=opt.get('value'),
                    emoji=discord.PartialEmoji(
                        name=opt['emoji']['name'],
                        id=opt['emoji'].get('id', None),  # Use None if there's no 'id' field
                        animated=opt['emoji'].get('animated', False)
                    ) if 'emoji' in opt else None,
                    default=opt.get('default', False))
                for opt in component_data.get('options', [])
            ]
        
            
            return DropDownSelect( 
                options=options,
                custom_id=component_data.get('custom_id'),
                placeholder=component_data.get('placeholder'),
                min_values=component_data.get('min_values', 1),
                max_values=component_data.get('max_values', 1)
            )
        
        else:
            raise ValueError(f"Unsupported component type: {component_type}")
    


def content_format(content):
    return "\n".join(content) if isinstance(content, list) else content

def get_message_from_template(template_name, variables = {}):
    
    file_path = f"templates/{template_name}.json"
    if not os.path.exists(file_path):
        raise ValueError(f"{template_name} doesn't not exists in messages templates.")
        
    template = {}
    with open(file_path, "r", encoding="utf-8") as f:
        template = json.load(f)
    
    if not template:
        raise ValueError("Message template cannot be empty.")
    
    return convert_to_message(template, variables)
    
def get_message_from_dict(dictionary, variables = {}):
    return convert_to_message(dictionary, variables)

def convert_to_message(template, variables={}):
    # define variables
    content = ""
    embeds = []
    # check if there's a text content 
    if "content" in template and template["content"] is not None:
        content = template.get("content", " ").format(**variables)
    # check for embeds 
    if "embeds" in template and template["embeds"] is not None:
        for embed in template["embeds"]:
            color = embed.get("color", "#ff4af0")
            if "ff4af0" in color:
                color = primary
            discord_embed = discord.Embed(
                title = content_format(embed.get("title", "")).format(**variables),
                description = content_format(embed.get("description", "")).format(**variables),
                color = int(embed.get("color", "#ff4af0").lstrip("#"), 16) if not isinstance(color, int) else color
            )
            # add author
            if "author" in embed and embed["author"] is not None:
                discord_embed.set_author(
                    name = content_format(embed["author"].get("name", "")).format(**variables), 
                    url = embed["author"].get("url", "").format(**variables), 
                    icon_url = embed["author"].get("icon_url", "").format(**variables)
                )
            # add fields
            if "fields" in embed and embed["fields"] is not None:
                for field in embed["fields"]:
                    discord_embed.add_field(
                        name=content_format(field.get("name", "")).format(**variables),
                        value=content_format(field.get("value", "")).format(**variables),
                        inline=field.get("inline", False)
                    )
            # add thumbnail
            if "thumbnail" in embed and embed["thumbnail"] is not None:
                thumbnail = embed["thumbnail"]
                thumbnail_url = thumbnail.get("url", "") if isinstance(thumbnail, dict) else thumbnail
                discord_embed.set_thumbnail(url=thumbnail_url.format(**variables))
            # add image 
            if "image" in embed and embed["image"] is not None:
                image = embed["image"]
                image_url = image.get("url", "") if isinstance(image, dict) else image
                discord_embed.set_image(url=image_url.format(**variables))
            # add footer
            if "footer" in embed and embed["footer"] is not None:
                discord_embed.set_footer(
                    text=content_format(embed["footer"].get("text", "")).format(**variables), 
                    icon_url=embed["footer"].get("icon_url", "").format(**variables)
                )
            # add timestamp
            if "timestamp" in embed and embed["timestamp"] is not None:
                discord_embed.set_footer(text=discord_embed.footer.text, icon_url=discord_embed.footer.icon_url)  # Ensure the footer is set
                timestamp = embed.get("timestamp", None)
                if timestamp == "{timestamp}":
                    timestamp = time.time()
                if isinstance(timestamp, (int, float)):
                    discord_embed.timestamp = datetime.fromtimestamp(timestamp)
                else:
                    discord_embed.timestamp = None
            embeds.append(discord_embed)
        
        # Add components 
        view = None
        if "components" in template and template["components"] is not None:
            view = PersistentView(template["components"])
            
    return {"content": content, "embeds": embeds, "view": view}