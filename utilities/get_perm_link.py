from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
import aiohttp
import discord
import os
import mimetypes
import re
import time

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = './service_account.json'
PARENT_FOLDER_ID = "11-JX_0n3xIgykj5AuDY-g16noar6aJ7o"


def authenticate():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds
    
def upload_photo(file_path):
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)
    
    # Get MIME type of the file
    mime_type, _ = mimetypes.guess_type(file_path)
    
    if not mime_type:
        mime_type = "application/octet-stream"  # Default type if MIME type cannot be detected
    
    # Prepare the file metadata for the upload
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [PARENT_FOLDER_ID]
    }

    # Upload the file with its MIME type
    media = MediaFileUpload(file_path, mimetype=mime_type)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media
    ).execute()
    
    os.remove(file_path)
    
    # Make the file public
    service.permissions().create(
        fileId=file['id'],
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()
    
    # Return the shareable link
    return f"https://drive.google.com/uc?export=download&id={file['id']}"
    
def delete_drive_file(drive_link):
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)
    match = re.search(r"id=([\w-]+)", drive_link)
    file_id = match.group(1)
    
    try:
        service.files().delete(fileId=file_id).execute()
    except Exception as e:
        print(f"Error deleting file from drive: {e}")

async def get_link(attachment: discord.Attachment):
    file_path = f"./storage/{int(time.time())}_{attachment.filename}" 
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Download the file from Discord
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            with open(file_path, "wb") as f:
                f.write(await resp.read())
        
    # Upload the file to Google Drive and get the shareable link
    link = upload_photo(file_path)
    return link