#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "requests",
#   "google-api-python-client",
#   "google-auth-httplib2",
#   "google-auth-oauthlib"
# ]
# ///

import os
from google.auth.transport.requests import Request  # pyrefly: ignore [missing-import]
from google.oauth2.credentials import Credentials  # pyrefly: ignore [missing-import]
from google_auth_oauthlib.flow import InstalledAppFlow  # pyrefly: ignore [missing-import]
from googleapiclient.discovery import build  # pyrefly: ignore [missing-import]
from googleapiclient.http import MediaFileUpload  # pyrefly: ignore [missing-import]

# Use drive.file for safety (least privilege needed to create & upload)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_drive():
    token_filename = 'my-google_token.json'
    """Handles OAuth2 authentication and returns a Drive service instance."""
    creds = None
    # token.json stores the user's access and refresh tokens
    if os.path.exists(token_filename):
        creds = Credentials.from_authorized_user_file(token_filename, SCOPES)
    
    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('google_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for future runs
        with open(token_filename, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def create_drive_folder(service, folder_name, parent_id):
    """Creates a subfolder inside a specified parent Drive folder."""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    
    # supportsAllDrives=True ensures compatibility with Shared Drives
    folder = service.files().create(
        body=file_metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()
    
    return folder.get('id')


def upload_file_to_drive(service, local_file_path, parent_id):
    """Uploads a single file to a specified Drive folder."""
    file_name = os.path.basename(local_file_path)
    file_metadata = {
        'name': file_name,
        'parents': [parent_id]
    }
    
    # Resumable upload for reliable transmission
    media = MediaFileUpload(local_file_path, resumable=True)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name',
        supportsAllDrives=True
    ).execute()    
    # print(f"  ✓ Uploaded file: {file_name}")

def upload_folder(shared_folder_id, created_folder_name, local_folder_path):
    upload_ok = True
    if not os.path.isdir(local_folder_path):
        print(f'Error: local directory named {local_folder_path} does not exist - not uploading files.')
        return False
    try:
        service = authenticate_drive()
        created_folder_id = create_drive_folder(service, created_folder_name, shared_folder_id)
        for (root, dirs, files) in os.walk(local_folder_path):
            if len(files) == 0:
                print('No files to upload')
            else:
                print(f'Uploading {len(files)} files')
            for f in files:
                local_file_path = os.path.join(root, f)
                upload_file_to_drive(service, local_file_path, created_folder_id)
        print(f"\n ---- Upload to {created_folder_name} folder finished  ----")
    #     upload_directory_recursive(service, LOCAL_FOLDER_PATH, SHARED_FOLDER_ID)
    #     print("\n Upload complete!")
    except Exception as e:
        print(f"\nError occurred: {e}")
        upload_ok = False
    return upload_ok

'''
def upload_directory_recursive(service, local_dir_path, drive_parent_id):
    #Recursively uploads a local folder and its contents to Google Drive.
    dir_name = os.path.basename(os.path.normpath(local_dir_path))
    print(f"\n📁 Creating target folder on Drive: '{dir_name}'...")
    
    # Create the root folder in Drive
    current_drive_folder_id = create_drive_folder(service, dir_name, drive_parent_id)
    
    # Mapping of local folder paths -> corresponding Drive folder IDs
    folder_mapping = {os.path.abspath(local_dir_path): current_drive_folder_id}

    for root, dirs, files in os.walk(local_dir_path):
        current_parent_drive_id = folder_mapping[os.path.abspath(root)]
        
        # 1. Create subdirectories in Drive
        for d in dirs:
            local_subfolder_path = os.path.join(root, d)
            print(f"Creating subfolder: {d}")
            new_drive_id = create_drive_folder(service, d, current_parent_drive_id)
            folder_mapping[os.path.abspath(local_subfolder_path)] = new_drive_id

        # 2. Upload files into current folder level
        for f in files:
            local_file_path = os.path.join(root, f)
            upload_file_to_drive(service, local_file_path, current_parent_drive_id)
'''

if __name__ == '__main__':
    SHARED_FOLDER_ID = '1EI9SuqrfZw2rwTKc0Wqw-Ks9uUxDc4P2'  # Target shared folder ID from Drive URL (Tags folder)
    NEW_FOLDER_NAME = 'example'
    LOCAL_FOLDER_PATH = './output_files'  # Path to local folder to upload
    upload_folder(SHARED_FOLDER_ID, NEW_FOLDER_NAME, LOCAL_FOLDER_PATH)
