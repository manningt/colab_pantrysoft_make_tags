#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "requests",
#   "fpdf2", 
#   "google-api-python-client",
#   "google-auth-httplib2",
#   "google-auth-oauthlib"
# ]
# ///

from upload_folder_to_gdrive import upload_folder
import os, sys
import subprocess
from datetime import datetime, timedelta
import time as unix_time
import json
import requests
import enum

from defines import GUEST_LIST_IDX_E

from get_guests_visits import load_token, get_client_lists, get_visits
from make_bag_tags_and_report import make_label_pdfs, write_report_pdf_file
from upload_folder_to_gdrive import authenticate_drive, create_drive_folder, upload_file_to_drive

from google.auth.transport.requests import Request # pyrefly: ignore [missing-import]
from google.oauth2.credentials import Credentials # pyrefly: ignore [missing-import]
from google_auth_oauthlib.flow import InstalledAppFlow # pyrefly: ignore [missing-import]
from googleapiclient.discovery import build # pyrefly: ignore [missing-import]
from googleapiclient.http import MediaFileUpload # pyrefly: ignore [missing-import]

def print_file(file_path: str, printer_name: str = None, copies: int = 1):
   # Prints a file using the CUPS/bash 'lp' command.
   cmd = ["lp"]
   if printer_name:
      cmd.extend(["-d", printer_name])
   if copies > 1:
      cmd.extend(["-n", str(copies)])
      cmd.extend(["-o", "collate=true"])
   cmd.append(file_path)

   try:
      result = subprocess.run(cmd, check=True, capture_output=True, text=True)
      print("Success: ", end='')
      print(result.stdout.strip())
      
   except FileNotFoundError:
      print("Error: The 'lp' command was not found. Ensure CUPS is installed and available in PATH.", file=sys.stderr)
   except subprocess.CalledProcessError as e:
      print(f"Printing failed (exit code {e.returncode}):", file=sys.stderr)
      print(e.stderr.strip(), file=sys.stderr)

if __name__ == "__main__":
   print(f'Generating report & tag PDFs using PantrySoft API at {datetime.now()}\n')
   pantrysoft_token = load_token("my-pantrysoft_token.json")

   TEMPORARY_CLIENT_LIST_FILENAME = "my-guests.json"

   # the client_info_dict is use to fill in the Last, First and Delivery Route when the guest_lists are generated
   #client_info_dict={'1': ['Cindy', 'Walsh', '04 - JSM'], '2': ['Linda', 'Webb', '20 - Quaker'],

   if not os.path.isfile(TEMPORARY_CLIENT_LIST_FILENAME):
      client_info_dict = get_client_lists(pantrysoft_token)
      MINIMUM_CLIENT_COUNT = 60
      if len(client_info_dict) < MINIMUM_CLIENT_COUNT:
         print(f"Error: number of clients is less than {MINIMUM_CLIENT_COUNT}")
         exit()
      with open(TEMPORARY_CLIENT_LIST_FILENAME, "w") as fp:
         json.dump(client_info_dict , fp)
   else:
      with open(TEMPORARY_CLIENT_LIST_FILENAME, "r") as fp:
         client_info_dict = json.load(fp)
      print(f'Using saved guest file {TEMPORARY_CLIENT_LIST_FILENAME} which has {len(client_info_dict)} guests', flush=True)

   # if run autonomously, check that it's Thursday
   if datetime.now().weekday() != 3:
      this_weeks_dates = ["2026-07-24", "2026-07-25"]
      print(f'Warning: using hardcoded dates: {this_weeks_dates}')
   else:
      Fridays_date = datetime.today() + timedelta(days=1)
      Saturdays_date = datetime.today() + timedelta(days=2)
      this_weeks_dates = [Fridays_date.strftime('%Y-%m-%d'), Saturdays_date.strftime('%Y-%m-%d')]

   # the four guest_visit_lists enumerated by GUEST_LIST_IDX_E;  the array is created here and filled in by the function
   guest_visit_lists = get_visits(pantrysoft_token, this_weeks_dates, client_info_dict)

   ''' example list:
   Friday_before_3
	   0 ('Timothy', 'Janvrin', '02:50 PM', 34)
	   1 ('John', 'Crowley', '02:50 PM', 18)
	   2 ('Denise', 'Logan', '02:50 PM', 27)
   Friday_after_3
	   0 ('Dionisio', 'Cruz', '05:00 PM', 53)
	   1 ('Marie', 'Deuerlein', '04:50 PM', 41)
   '''

   output_directory = "./output_files"
   status_strings = []
   for list_idx, guest_list in enumerate(guest_visit_lists):
      if list_idx == GUEST_LIST_IDX_E.Delivery.value:
         guest_list.sort(key=lambda x: (x[2], x[1]))  #sort by delivery_route, last name
         type = 'Delivery'
         # print(f"{list_idx=} {GUEST_LIST_IDX_E(list_idx).name} sorting by route")
      else:
         guest_list.sort(key=lambda x: (x[1], x[0]))  #sort by last name, first name; pickup time is not used on label
         # print(f"{list_idx=} {GUEST_LIST_IDX_E(list_idx).name} sorting by last name, first name")
         type = 'Pickup'

      if 0:
         print(f"{GUEST_LIST_IDX_E(list_idx).name}")
         for idx, guest in enumerate(guest_list):
            print(f"\t{idx} {guest}")

      pdf_filename = f'tags-for-{GUEST_LIST_IDX_E(list_idx).name}.pdf'
      status_string = make_label_pdfs(guest_list, type, pdf_filename, output_directory)
      print(status_string)
      status_strings.append(status_string)
      
   write_report_pdf_file(guest_visit_lists, status_strings, output_directory)

   text_report_path = os.path.join(output_directory, "make_tags_report.txt")
   with open(text_report_path, "w") as report_file:
      for line in status_strings:
         report_file.write(line + "\n")

   # report generation done, now upload to google drive
   print('Uploading generated PDFs to /Newbury Food Pantry/PANTRYSOFT ORDER DOCUMENTS/20xx/Tags')
   SHARED_FOLDER_ID = '1EI9SuqrfZw2rwTKc0Wqw-Ks9uUxDc4P2'  # Target shared folder ID from Drive URL (Tags folder)
   new_folder_name = datetime.today().strftime('%B-%d-tags') #full month name, day
   LOCAL_FOLDER_PATH = './output_files'  # Path to local folder to upload
   upload_folder(SHARED_FOLDER_ID, new_folder_name, LOCAL_FOLDER_PATH)

   # now print
   print_file('/home/pantry/repos/generate_pantry_PDFs/output/list-of-guests-in-tag-pdf-files.pdf')