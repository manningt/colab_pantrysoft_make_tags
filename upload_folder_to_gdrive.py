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
from googleapiclient.errors import HttpError  # pyrefly: ignore [missing-import]
from datetime import datetime


# Use drive.file for safety (least privilege needed to create & upload)
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.file']

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

def upload_folder(local_folder_path, shared_folder_id, created_folder_name = None):
    upload_ok = True
    if not os.path.isdir(local_folder_path):
        print(f'Error: local directory named {local_folder_path} does not exist - not uploading files.')
        return False
    try:
        service = authenticate_drive()
        if created_folder_name:
            folder_id_for_upload = create_drive_folder(service, created_folder_name, shared_folder_id)
            upload_folder_name = created_folder_name
        else:
            folder_id_for_upload = shared_folder_id
            upload_folder_name = shared_folder_id
        for (root, dirs, files) in os.walk(local_folder_path):
            if len(files) == 0:
                print('No files to upload')
            else:
                print(f'Uploading {len(files)} files to {upload_folder_name}: ', end="")
                for f in files:
                    local_file_path = os.path.join(root, f)
                    upload_file_to_drive(service, local_file_path, folder_id_for_upload)
                print(f"Fini")
    except Exception as e:
        print(f"\nError occurred: {e}")
        upload_ok = False
    return upload_ok


def get_folder_id(top_level_shared_folder, date_list, create_if_not_present=False):
    # date_list = ["2027", "February", "05"]
    folder_path = ""
    if len(date_list) == 3:
        folder_id = top_level_shared_folder    
        for i in range(3):
            # print(f"\n{i=}: list_folder_contents for {folder_id=}")
            items = list_folder_contents(folder_id)
            higher_level_folder_id = folder_id
            folder_id = None
            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    if i < 2 and item['name'] == date_list[i]:
                        #year, month
                        folder_id = item['id']
                        folder_path += f"{item['name']}/"
                    else:
                        #separate month and day: month will be [0], day will be [1]
                        parsed_folder_name = item['name'].replace('-', ' ').replace('_', ' ').split(" ")
                        # compare 3 characters of month with folder name and integer of day
                        month_abbrev = date_list[1][:3]
                        # print(f"{month_abbrev=}")
                        if parsed_folder_name[0].startswith(month_abbrev) and int(parsed_folder_name[1]) == int(date_list[2]):
                            folder_id = item['id']
                            folder_path += f"{item['name']}/"
                if folder_id:
                    # print(f"found folder: {item['name']} (ID: {item['id']})")
                    break

            if not folder_id:
                if create_if_not_present:
                    service = authenticate_drive()
                    if i < 2:
                        folder_name_to_create = date_list[i]
                    else:
                        folder_name_to_create = f"{date_list[1][:3]} {int(date_list[2])}"
                    # print(f"Creating {folder_name_to_create}")
                    folder_id = create_drive_folder(service, folder_name_to_create, higher_level_folder_id)
                    folder_path += f"{folder_name_to_create}/"
                else:
                    print(f"Did not find folder for {date_list[i]} when searching for date: {date_list}")
                    break
    else:
        print(f"Bad date list: {date_list}")
        folder_id = None

    return folder_id, folder_path


def list_folder_contents(folder_id: str):
    items = []
    try:
        service = authenticate_drive()

        # Query filter:
        # 1. 'folder_id' in parents -> directly inside the specified folder
        # 2. trashed = false        -> exclude items in the bin/trash
        query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

        page_token = None

        while True:
            response = service.files().list(
                q=query,
                fields='nextPageToken, files(id, name, mimeType)',
                spaces='drive',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageToken=page_token
            ).execute()

            items.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            
            if not page_token:
                break

    except HttpError as error:
        print(f"An error occurred: {error}")

    return items

'''
def upload_directory_recursive(service, local_dir_path, drive_parent_id):
    #Recursively uploads a local folder and its contents to Google Drive.
    dir_name = os.path.basename(os.path.normpath(local_dir_path))
    print(f"\n Creating target folder on Drive: '{dir_name}'...")
    
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

    now = datetime.now()
    PANTRYSOFT_ORDER_DOCUMENTS_FOLDER_ID = '1qusUE0OHeK7-i-Tu647dsQJ7nC12uVVz' # Newbury Food Pantry > PANTRYSOFT ORDER DOCUMENTS


    TEST_CREATE_DATE_FOLDER = True
    if TEST_CREATE_DATE_FOLDER:
        date_list = ["2027", "March", "05"]
        this_weeks_folder_id, folder_path = \
            get_folder_id(PANTRYSOFT_ORDER_DOCUMENTS_FOLDER_ID, date_list, create_if_not_present=True)
        if not this_weeks_folder_id:
            print('error: this weeks folder not found')
        else:
            print(f'{folder_path=} {this_weeks_folder_id=}')


    TEST_GET_FOLDER_ID_WITHOUT_CREATE = False
    if TEST_GET_FOLDER_ID_WITHOUT_CREATE:
        date_list = [now.strftime('%Y'), now.strftime('%B'), now.strftime('%d')]
        test_date_lists = [['2026', 'September'], ['2026', 'September', '4'], date_list]
        for i in range (3):
            this_weeks_folder_id, folder_path = get_folder_id(PANTRYSOFT_ORDER_DOCUMENTS_FOLDER_ID, test_date_lists[i])
            if not this_weeks_folder_id:
                print('error: this weeks folder not found')
            else:
                print(f'{folder_path=} {this_weeks_folder_id=}')


    TEST_LIST_FOLDER_CONTENTS = False
    if TEST_LIST_FOLDER_CONTENTS:
        items = list_folder_contents(PANTRYSOFT_ORDER_DOCUMENTS_FOLDER_ID)
        if len(items) == 0:
            print("No files or folders found")
        else:
            for item in items:
                item_type = "[FOLDER]" if item['mimeType'] == 'application/vnd.google-apps.folder' else "[FILE]"
                print(f"{item_type} {item['name']} (ID: {item['id']})")


    TEST_UPLOAD_TO_NEW_FOLDER = False
    if TEST_UPLOAD_TO_NEW_FOLDER:
        SHARED_FOLDER_ID = '1EI9SuqrfZw2rwTKc0Wqw-Ks9uUxDc4P2'  #folder ID from Drive URL: Newbury Food Pantry > PANTRYSOFT ORDER DOCUMENTS > 2026 > Tags
        NEW_FOLDER_NAME = 'example'
        LOCAL_FOLDER_PATH = './output_files'  # Path to local folder to upload
        upload_folder(SHARED_FOLDER_ID, NEW_FOLDER_NAME, LOCAL_FOLDER_PATH)


    #SHARED_FOLDER_ID = '1fe1J4Un0bw3vqtge0tvBu9Nx4JcXT4nu'  # Newbury Food Pantry > PANTRYSOFT ORDER DOCUMENTS > 2026
