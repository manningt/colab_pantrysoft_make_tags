#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "google-api-python-client",
#   "google-auth-httplib2",
#   "google-auth-oauthlib"
# ]
# ///

import datetime
from upload_folder_to_gdrive import get_folder_id
from calendar import month_name

today = datetime.date.today()
this_coming_friday = today + datetime.timedelta( (4-today.weekday()) % 7 )
this_coming_friday_list = this_coming_friday.strftime('%Y-%m-%d').split('-')
this_coming_friday_list[1] = month_name[int(this_coming_friday_list[1])] #get name from month number

PANTRYSOFT_ORDER_DOCUMENTS_FOLDER_ID = '1qusUE0OHeK7-i-Tu647dsQJ7nC12uVVz'
this_weeks_folder_id, this_weeks_folder_path, created_folder_list = \
   get_folder_id(PANTRYSOFT_ORDER_DOCUMENTS_FOLDER_ID, this_coming_friday_list)
# print(f"{this_weeks_folder_id=} {this_weeks_folder_path=}")
if this_weeks_folder_id:
   if len(created_folder_list):
      print(f"Made folders: {", ".join(created_folder_list)}")
   else:
      print(f"Folders for {"-".join(this_coming_friday_list)} already exist.")
else:
   print(f"Failed to make folder for {"-".join(this_coming_friday_list)}")
