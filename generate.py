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
from calendar import month_name
import json

from google.auth.transport.requests import Request # pyrefly: ignore [missing-import]
from google.oauth2.credentials import Credentials # pyrefly: ignore [missing-import]
from google_auth_oauthlib.flow import InstalledAppFlow # pyrefly: ignore [missing-import]
from googleapiclient.discovery import build # pyrefly: ignore [missing-import]
from googleapiclient.http import MediaFileUpload # pyrefly: ignore [missing-import]

from defines import GUEST_LIST_IDX_E
from get_guests_visits import load_token, get_client_lists, get_visits
# from get_registrations import get_registrations, make_priority_landline_lists
from make_bag_tags_and_report import make_label_pdfs, write_tag_report_pdf, \
   write_expeditor_2column_pdf, move_delivery_to_pickup, write_expeditor_1column_pdf, \
   write_delivery_routes_pdf
from make_csv import write_csv
from make_delivery_tally import write_delivery_tally_csv
from upload_folder_to_gdrive import upload_folder, get_folder_id


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
   now = datetime.now()
   print(f'Generating report & tag PDFs using PantrySoft API at {now}')

   # if run autonomously, check that it's Thursday
   if now.weekday() != 3:
      this_weeks_dates = ["2026-08-28", "2026-08-29"]
      print(f'\tWarning: using hardcoded dates: {this_weeks_dates}')
   else:
      Fridays_date = now + timedelta(days=1)
      Saturdays_date = now + timedelta(days=2)
      this_weeks_dates = [Fridays_date.strftime('%Y-%m-%d'), Saturdays_date.strftime('%Y-%m-%d')]

   gdrive_folder_path_list = this_weeks_dates[0].split("-")
   gdrive_folder_path_list[1] = month_name[int(gdrive_folder_path_list[1])] #get name from month number
   PANTRYSOFT_ORDER_DOCUMENTS_FOLDER_ID = '1qusUE0OHeK7-i-Tu647dsQJ7nC12uVVz'
   this_weeks_folder_id, this_weeks_folder_path, created_folder_list = \
      get_folder_id(PANTRYSOFT_ORDER_DOCUMENTS_FOLDER_ID, gdrive_folder_path_list)
   # print(f"{this_weeks_folder_id=} {this_weeks_folder_path=}")
   if not this_weeks_folder_id:
      print(f"Quitting: The folder for {gdrive_folder_path_list} does not exist.")
      exit()

   # if not run at 12, must be testing
   if now.hour != 12:
      test_mode = True
      print("Using test mode which skips printing")
   else:
      test_mode = False

   try:
      pantrysoft_token = load_token("my-pantrysoft_token.json")
   except:
      print("Quitting: PantrySoft token failed to load.")
      exit()

   LOCAL_FOLDER_PATH = './output_files'  # Path to local folder which contains the report & tag PDFs that will be uploaded to the google drive
   files_to_print = []

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
      if len(guest_visit_lists[0]) < 1:
         print(f"Quiting: no visits found for {this_weeks_dates}")
      else:
         with open(TEMPORARY_GUEST_VISIT_LIST_FILENAME, "w") as fp:
            json.dump(guest_visit_lists , fp)
   else:
      with open(TEMPORARY_GUEST_VISIT_LIST_FILENAME, "r") as fp:
         guest_visit_lists = json.load(fp)
      print(f'Using saved visits file {TEMPORARY_GUEST_VISIT_LIST_FILENAME}', flush=True)

   # some deliveries are picked-up at a certain time, so move them from deliveries to pickup:
   modified_guest_visit_lists = move_delivery_to_pickup(guest_visit_lists,[('Quak','03:45')])
   #sort:
   for list_idx, guest_list in enumerate(modified_guest_visit_lists): #guest_visit_lists):
      if list_idx == GUEST_LIST_IDX_E.Delivery.value:
         guest_list.sort(key=lambda x: (x[3], x[4]))  #sort by delivery_route, last_name 
      else:
         guest_list.sort(key=lambda x: (x[2], x[3]))  #sort by time and last_name for the pickup report

   write_csv(modified_guest_visit_lists, LOCAL_FOLDER_PATH, f'_{this_weeks_dates[0][-5:]}.csv', client_info_dict)

   delivery_tally_csv_filename = f'Delivery_Tally-{this_weeks_dates[0][-5:]}.csv'
   write_delivery_tally_csv(modified_guest_visit_lists[GUEST_LIST_IDX_E.Delivery.value], LOCAL_FOLDER_PATH, delivery_tally_csv_filename)

   delivery_pdf_filename = f'Deliveries_{this_weeks_dates[0][-5:]}.pdf'
   write_expeditor_1column_pdf(modified_guest_visit_lists, LOCAL_FOLDER_PATH, delivery_pdf_filename, client_info_dict, this_weeks_dates)
   files_to_print.append((delivery_pdf_filename,1)) #filename & copies tuple

   pickup_pdf_filename = f'Pickups_{this_weeks_dates[0][-5:]}.pdf'
   write_expeditor_2column_pdf(modified_guest_visit_lists, LOCAL_FOLDER_PATH, pickup_pdf_filename, client_info_dict, this_weeks_dates)
   files_to_print.append((pickup_pdf_filename,1))

   delivery_routes_pdf_filename = f'Deliveries_per_route_{this_weeks_dates[0][-5:]}.pdf'
   # the following list is case sensitive, e.g. 07A should be 07a
   delivery_routes_to_print = ["01", "04", "08", "09", "20"]
   write_delivery_routes_pdf(modified_guest_visit_lists, LOCAL_FOLDER_PATH, delivery_routes_pdf_filename, \
      client_info_dict, this_weeks_dates, delivery_routes_to_print)
   files_to_print.append((delivery_routes_pdf_filename,1))

   status_strings = []
   for list_idx, guest_list in enumerate(guest_visit_lists):
      guest_list.sort(key=lambda x: (x[3], x[4]))  #sort by delivery_route, last_name -or- last_name or first_name
      if list_idx == GUEST_LIST_IDX_E.Delivery.value:
         type = 'Delivery'
      else:
         type = 'Pickup'

      pdf_filename = f'tags-for-{GUEST_LIST_IDX_E(list_idx).name}.pdf'
      status_string = make_label_pdfs(guest_list, type, pdf_filename, LOCAL_FOLDER_PATH, client_info_dict)
      print(status_string)
      status_strings.append(status_string)

   TAG_PDF_REPORT_FILENAME = 'list-of-guests-in-tag-pdf-files.pdf'
   write_tag_report_pdf(guest_visit_lists, status_strings, LOCAL_FOLDER_PATH, TAG_PDF_REPORT_FILENAME, client_info_dict)
   files_to_print.append((TAG_PDF_REPORT_FILENAME,1))

   text_report_path = os.path.join(LOCAL_FOLDER_PATH, "make_tags_report.txt")
   with open(text_report_path, "w") as report_file:
      for line in status_strings:
         report_file.write(line + "\n")

   # report generation done, now upload to google drive
   print(f"Uploading generated files to /Newbury Food Pantry/PANTRYSOFT ORDER DOCUMENTS/{this_weeks_folder_path}: ", end=None, flush=True)
   upload_folder(LOCAL_FOLDER_PATH, this_weeks_folder_id)

   # now print
   for file_copies_tuple in files_to_print:
      if test_mode:
         print(f'Test mode: skipping printing of {file_copies_tuple[1]} copies of {file_copies_tuple[0]}')
      else:
         print(f'Printing {file_copies_tuple[1]} copies of {file_copies_tuple[0]}')
         print_file(os.path.join(LOCAL_FOLDER_PATH, file_copies_tuple[0]), copies=file_copies_tuple[1])