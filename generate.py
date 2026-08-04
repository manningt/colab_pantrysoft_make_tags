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

import os, sys
import subprocess
from datetime import datetime, timedelta
import json

from defines import GUEST_LIST_IDX_E

from get_guests_visits import load_token, get_client_lists, get_visits
from make_bag_tags_and_report import make_label_pdfs, write_tag_report_pdf, write_pickup_expeditor_pdf
from upload_folder_to_gdrive import upload_folder

# from google.auth.transport.requests import Request # pyrefly: ignore [missing-import]
# from google.oauth2.credentials import Credentials # pyrefly: ignore [missing-import]
# from google_auth_oauthlib.flow import InstalledAppFlow # pyrefly: ignore [missing-import]
# from googleapiclient.discovery import build # pyrefly: ignore [missing-import]
# from googleapiclient.http import MediaFileUpload # pyrefly: ignore [missing-import]

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

   # if run autonomously, check that it's Thursday
   if datetime.now().weekday() != 3:
      this_weeks_dates = ["2026-07-31", "2026-08-01"]
      print(f'Warning: using hardcoded dates: {this_weeks_dates}')
   else:
      Fridays_date = datetime.today() + timedelta(days=1)
      Saturdays_date = datetime.today() + timedelta(days=2)
      this_weeks_dates = [Fridays_date.strftime('%Y-%m-%d'), Saturdays_date.strftime('%Y-%m-%d')]

   LOCAL_FOLDER_PATH = './output_files'  # Path to local folder which contains the report & tag PDFs that will be uploaded to the google drive
   TAG_PDF_REPORT_FILENAME = 'list-of-guests-in-tag-pdf-files.pdf'

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
      print(f'Using saved guest/client file {TEMPORARY_CLIENT_LIST_FILENAME} which has {len(client_info_dict)} guests', flush=True)

   ''' 
   # the four guest_visit_lists enumerated by GUEST_LIST_IDX_E;  the array is created here and filled in by the function
   example list
   Friday_before_3
	   0 (client_id, item_count, pickup_time or None, delivery_route or last_name. last_name or first_name)
   Friday_after_3

   Note: the last 2 items (item 3 & 4) in the row's list are for sorting.
   '''

   TEMPORARY_GUEST_VISIT_LIST_FILENAME = "my-visit-lists.json"
   if not os.path.isfile(TEMPORARY_GUEST_VISIT_LIST_FILENAME):
      guest_visit_lists = get_visits(pantrysoft_token, this_weeks_dates, client_info_dict)
      with open(TEMPORARY_GUEST_VISIT_LIST_FILENAME, "w") as fp:
         json.dump(guest_visit_lists , fp)
   else:
      with open(TEMPORARY_GUEST_VISIT_LIST_FILENAME, "r") as fp:
         guest_visit_lists = json.load(fp)
      print(f'Using saved guest file {TEMPORARY_GUEST_VISIT_LIST_FILENAME}', flush=True)

   pickup_pdf_filename = f'Pickup_expeditor_{this_weeks_dates[0][-5:]}.pdf'
   write_pickup_expeditor_pdf(guest_visit_lists, LOCAL_FOLDER_PATH, pickup_pdf_filename, client_info_dict, this_weeks_dates)
   # exit()

   status_strings = []
   for list_idx, guest_list in enumerate(guest_visit_lists):
      guest_list.sort(key=lambda x: (x[3], x[4]))  #sort by delivery_route, last_name -or- last_name, first_name
      if list_idx == GUEST_LIST_IDX_E.Delivery.value:
         type = 'Delivery'
      else:
         type = 'Pickup'

      pdf_filename = f'tags-for-{GUEST_LIST_IDX_E(list_idx).name}.pdf'
      status_string = make_label_pdfs(guest_list, type, pdf_filename, LOCAL_FOLDER_PATH, client_info_dict)
      print(status_string)
      status_strings.append(status_string)
      
   write_tag_report_pdf(guest_visit_lists, status_strings, LOCAL_FOLDER_PATH, TAG_PDF_REPORT_FILENAME, client_info_dict)

   text_report_path = os.path.join(LOCAL_FOLDER_PATH, "make_tags_report.txt")
   with open(text_report_path, "w") as report_file:
      for line in status_strings:
         report_file.write(line + "\n")

   # report generation done, now upload to google drive
   print('Uploading generated PDFs to /Newbury Food Pantry/PANTRYSOFT ORDER DOCUMENTS/20xx/Tags')
   SHARED_FOLDER_ID = '1EI9SuqrfZw2rwTKc0Wqw-Ks9uUxDc4P2'  # Target shared folder ID from Drive URL (Tags folder)
   new_folder_name = datetime.today().strftime('%B-%d-tags') #full month name, day
   upload_folder(SHARED_FOLDER_ID, new_folder_name, LOCAL_FOLDER_PATH)

   # now print
   tag_pdf_report_path = os.path.join(LOCAL_FOLDER_PATH, TAG_PDF_REPORT_FILENAME)
   print_file(tag_pdf_report_path)