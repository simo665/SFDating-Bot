import os
import discord
from discord.ext import tasks, commands
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

# Load Google Drive credentials
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
service = build("drive", "v3", credentials=creds)

# File details
LOCAL_FILES = ["database/data.db", "database/data2.db"]
FOLDER_ID = "11MFLDzhQvLMGTdPe0uThY2dkcQfXvlE9"  


def get_file_id(filename):
    """Check if the file already exists on Google Drive."""
    query = f"name='{filename}' and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None

def upload_database():
    """Upload or update the database file in Google Drive."""
    
    for LOCAL_FILE in LOCAL_FILES:
        if not os.path.exists(LOCAL_FILE):
            print(f"File {LOCAL_FILE} not found locally, skipping upload.")
            continue
        
        file_id = get_file_id(LOCAL_FILE)
    
        if file_id:
            # Replace the old file
            file_metadata = {"name": LOCAL_FILE}
            media = MediaFileUpload(LOCAL_FILE, resumable=True)
            try:
                service.files().update(fileId=file_id, media_body=media).execute()
                print(f"Updated: {LOCAL_FILE} on Google Drive")
            except Exception as e:
                print(f"Failed to update {LOCAL_FILE}: {e}")
        else:
            # Upload as a new file
            file_metadata = {"name": LOCAL_FILE}
            if FOLDER_ID:
                file_metadata["parents"] = [FOLDER_ID]
            media = MediaFileUpload(LOCAL_FILE, resumable=True)
            try:
                service.files().create(body=file_metadata, media_body=media).execute()
                print(f"Uploaded: {LOCAL_FILE} to Google Drive")
            except Exception as e:
                print(f"Failed to upload {LOCAL_FILE}: {e}")