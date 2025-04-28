import os
import re
import aiohttp
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger('bot.gdrive')

# Google Drive API configuration
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'
PARENT_FOLDER_ID = "12yysGhBxeI4oUd9QdABRvQcBsDBY5Mg5"  # Root folder for all server assets

def authenticate():
    """Authenticate with Google Drive API using service account"""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return creds
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None

def get_or_create_folder(service, server_id, parent_folder_id):
    """Get or create a folder for a specific server"""
    try:
        # Check if folder exists
        query = f"'{parent_folder_id}' in parents and name='{server_id}' and mimeType='application/vnd.google-apps.folder'"
        results = service.files().list(q=query, fields="files(id)").execute()
        folders = results.get("files", [])

        if folders:
            return folders[0]["id"]  

        # Create the folder if it does not exist
        folder_metadata = {
            "name": str(server_id),
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id]
        }
        folder = service.files().create(body=folder_metadata, fields="id").execute()
        return folder["id"]
    except Exception as e:
        logger.error(f"Error with folder creation: {e}")
        return None

def upload_file(file_path, server_id):
    """Upload a file to Google Drive and return the public URL"""
    try:
        creds = authenticate()
        if not creds:
            return None
            
        service = build('drive', 'v3', credentials=creds)
        server_folder_id = get_or_create_folder(service, server_id, PARENT_FOLDER_ID)
        
        if not server_folder_id:
            return None
            
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [server_folder_id]
        }

        # Upload the file
        file = service.files().create(
            body=file_metadata,
            media_body=file_path
        ).execute()
        
        # Clean up the temporary file
        os.remove(file_path)
        
        # Make file publicly accessible
        service.permissions().create(
            fileId=file['id'],
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        # Return the direct download link
        return f"https://drive.google.com/uc?export=download&id={file['id']}"
    except Exception as e:
        logger.error(f"File upload error: {e}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        return None

def delete_drive_file(drive_link):
    """Delete a file from Google Drive using its URL"""
    try:
        if not drive_link or 'drive.google.com' not in drive_link:
            return False
            
        creds = authenticate()
        if not creds:
            return False
            
        service = build('drive', 'v3', credentials=creds)
        
        # Extract file ID from the URL
        match = re.search(r"id=([\w-]+)", drive_link)
        if not match:
            return False
            
        file_id = match.group(1)
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting file from drive: {e}")
        return False

async def get_drive_url(attachment, server_id):
    """Process an attachment and upload it to Google Drive"""
    try:
        # Create temp directory if it doesn't exist
        os.makedirs('storage/temp', exist_ok=True)
        
        # Download the attachment
        file_path = f"storage/temp/{attachment.filename}" 
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    return None
                    
                with open(file_path, "wb") as f:
                    f.write(await resp.read())
        
        # Upload to Google Drive
        link = upload_file(file_path, str(server_id))
        return link
    except Exception as e:
        logger.error(f"Error processing attachment: {e}")
        return None