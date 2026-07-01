#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "requests",
#   "fpdf2"
# ]
# ///
'''
the 4 lists used by make_label_pdfs() are:
  Delivery, 'Saturday': (7, 12), 'Friday-before-3': (12, 15), 'Friday-after-3': (15, 23)}
      where each list is:
        tuples with the guest's first name, last name, route or pickup time, and item count

make 4 interim lists, where the list is a tuple: clientID, none, route or pickup time, and item count.
   then go and replace ClientID with first name, and None with Last Name, e.g.
      guest_list.append((row['First'], row['Last'], row['Route or Pickup Time'], item_count))

'''
from datetime import datetime
import time as unix_time
import os, sys
import json
import requests
import enum

sys.path.append('../pantry_labels')
from make_labels import make_label_pdfs, write_report_pdf_file

CONFIG_FILE = "my-config.json"

def load_token(config_path=CONFIG_FILE):
   """Loads the X-Auth-Token from the configuration file."""
   if not os.path.exists(config_path):
      raise FileNotFoundError(f"Configuration file '{config_path}' was not found.")
   try:
      with open(config_path, 'r', encoding='utf-8') as f:
         config = json.load(f)
         token = config.get("pantrysoft", {}).get("auth_token")
         if not token:
               raise ValueError("X-Auth-Token is empty or still set to the default placeholder.")
         return token
   except (json.JSONDecodeError, KeyError) as e:
      raise ValueError(f"Failed to parse configuration file '{config_path}': {e}")

FRIDAY_IDX = 0
SATURDAY_IDX = 1
FRIDAY_SPLIT_REPORT_HOUR = 3 # the time in the afternoon to split into before/after pickup lists

class GUEST_LIST_IDX_E(enum.Enum): 
   Pickup_Friday_before_3 = 0
   Pickup_Friday_after_3 = 1
   Pickup_Saturday = 2
   Delivery = 3

def parse_visit_response(response_data, guest_lists, this_weeks_dates, client_info_dict):
   done = False #only True when we hit a date out of range
   record_count = 0
   added_count = 0
   for visit_dict in response_data:
      guest_list_index = None
      record_count += 1
      item_count = 0
      for item_dict in visit_dict['inventory_visit_items']:
         item_count += item_dict['quantity']
      # print(f"{visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['visit_type']=} {visit_dict['client_id']=} {item_count=}")

      item_count = int(item_count)
      if item_count == 0:
         print(f"visit has no items: {visit_dict['visit_type']=} {visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['client_id']=}")
         continue

      client_id = visit_dict['client_id']
      first_name = client_info_dict[client_id][0]
      last_name = client_info_dict[client_id][1]
      delivery_route = client_info_dict[client_id][2]

      if visit_dict['visit_type'] == 'Delivery':
         # client_tuple = (visit_dict['client_id'], None, None, item_count)
         client_tuple = (first_name, last_name, delivery_route, item_count)
         guest_list_index = GUEST_LIST_IDX_E.Delivery.value
      elif visit_dict['visit_type'] == 'Pickup':
         date_str, time_str = visit_dict['visit_datetime'].split(' ')
         hour_str, minute_str, _ = time_str.split(':')
         try:
            pickup_hour = int(hour_str)
            pickup_minute = int(minute_str)
         except ValueError:
            print(f"time string not an integer: {visit_dict['visit_datetime']=} {visit_dict['id']=} {visit_dict['visit_type']=} {visit_dict['client_id']=}")
            exit()

         pickup_hour += 2 # adjust from Mountain Time to Eastern Time
         am_pm = "AM"
         if pickup_hour > 12:
            pickup_hour -= 12
            am_pm = "PM"
         pickup_time_str = f"{pickup_hour:02d}:{pickup_minute:02d} {am_pm}"

         # client_tuple = (visit_dict['client_id'], None, pickup_time_str, int(item_count))
         client_tuple = (first_name, last_name, pickup_time_str, item_count)
         if date_str == this_weeks_dates[FRIDAY_IDX]:
            if pickup_hour < FRIDAY_SPLIT_REPORT_HOUR:
               guest_list_index = GUEST_LIST_IDX_E.Pickup_Friday_before_3.value
            else:
               guest_list_index = GUEST_LIST_IDX_E.Pickup_Friday_after_3.value
         elif date_str == this_weeks_dates[SATURDAY_IDX]:
            guest_list_index = GUEST_LIST_IDX_E.Pickup_Saturday.value
         else:
            print(f"date out-of-range: {visit_dict['visit_datetime']=} {visit_dict['id']=} {visit_dict['visit_type']=} {visit_dict['client_id']=}")
            done = True
            break
      else:
         print(f"Unknown visit_type: {visit_dict['visit_type']=} {visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['client_id']=}")

      if guest_list_index is not None:
         guest_lists[guest_list_index].append(client_tuple)
         added_count += 1
      else:
         print(f"guest list index is None: {visit_dict['visit_type']=} {visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['client_id']=}")
   ''' example list before clientId substitution
   Saturday
      0 ('1134', None, '10:45 AM', 34)
      1 ('392', None, '10:30 AM', 37)
      2 ('905', None, '10:00 AM', 40)
   '''

   if record_count != added_count:
      print(f"Error: parse_visit_response added {added_count} visits but the {record_count=}; {done=}")
   return done, guest_lists


def get_visits(token, guest_lists, this_weeks_dates, client_info_dict):
   # there should be less than 450 visits
   RECORD_LIMIT = 50
   MAX_PAGE_NUMBER = 10

   url = "https://app.pantrysoft.com/api/v1/visit/"
   params = {
     "limit": RECORD_LIMIT,
      "sort": "visitDatetime",
      "order": "DESC",
      "aggregates": "false"
   }
   headers = {
      "accept": "application/json",
      "X-Auth-Token": token
   }

   total_visits = 0
   start_time = unix_time.time()
   print('Fetching visit pages', end='', flush=True)
   for page_number in range(1, MAX_PAGE_NUMBER):
      params["page"] = page_number
      response = requests.get(url, headers=headers, params=params)
      if response.status_code != 200:
         print(f"Request failed with status code {response.status_code}")
         print(response.text)
         exit()

      response_list = response.json()
      # next_page = response_list['next_page']

      done, guest_lists = parse_visit_response(response_list['data'], guest_lists, this_weeks_dates, client_info_dict)
      print(' .', end='', flush=True)
      if 0: 
         print(f"{page_number=} list_lengths: ", end="")
         for guest_list_index in GUEST_LIST_IDX_E:
            print(f"{guest_list_index.name}={len(guest_lists[guest_list_index.value])} ", end="")
         print()

      if done:
          break

   elapsed_time =  unix_time.time() - start_time
   average_time_per_page = page_number/elapsed_time
   for guest_list_index in GUEST_LIST_IDX_E:
      total_visits += len(guest_lists[guest_list_index.value])
   print(f' done: {total_visits} visits retrieved in {elapsed_time:.2f} seconds; average_per_page={average_time_per_page:.2f}', flush=True)

   return guest_lists

def parse_client_response(response_list, client_info_dict):
   record_count = 0
   added_count = 0
   for individual_client_dict in response_list:
      record_count += 1
      client_id = individual_client_dict['id']
      # if record_count == 1:
      #    print(f"DEBUG {individual_client_dict=}")

      if 'delivery_route_name' in individual_client_dict:
         delivery_route = individual_client_dict['delivery_route_name']
      else:
         delivery_route = 'None'

      if 'household_members' in individual_client_dict:
         added_count += 1
         client_info_dict[client_id] =[
            individual_client_dict['household_members'][0]['first_name'],
            individual_client_dict['household_members'][0]['last_name'], 
            delivery_route]
         if not individual_client_dict['household_members'][0]['is_primary']:
            print(f"Not is_primary: {client_info_dict[client_id]=}")
      else:
         print(f"{client_id=} has no household members")

   if record_count != added_count:
      print(f"Error: parse_client_response() added {added_count} but there were {record_count} records")
   return client_info_dict, added_count

def get_client_lists(token):
   # as of July 2026, there are about 800 active clients
   RECORD_LIMIT = 50
   MAX_PAGE_NUMBER = 24

   client_info_dict = {}

   url = "https://app.pantrysoft.com/api/v1/client/"
   params = {
     "limit": RECORD_LIMIT,
      "sort": "id",
      "order": "ASC",
      "active_only": "true"
   }
   headers = {
      "accept": "application/json",
      "X-Auth-Token": token
   }

   start_time = unix_time.time()
   print('Fetching client pages', end='', flush=True)
   for page_number in range(1, MAX_PAGE_NUMBER):
      params["page"] = page_number
      response = requests.get(url, headers=headers, params=params)
      if response.status_code != 200:
         print(f"Request failed with status code {response.status_code}")
         print(response.text)
         exit()

      response_list = response.json()
      client_info_dict, clients_added_count = parse_client_response(response_list['data'], client_info_dict)
      print(' .', end='', flush=True)
      if clients_added_count < RECORD_LIMIT:
         elapsed_time = unix_time.time() - start_time
         average_time_per_page = page_number/elapsed_time
         print(f' done: {len(client_info_dict)} active guests retrieved in {elapsed_time:.2f} seconds; average_per_page={average_time_per_page:.2f}', flush=True)
         break

   return client_info_dict

if __name__ == "__main__":
   token = load_token()
   TEMPORARY_CLIENT_LIST_FILENAME = "my-guests.json"

   # the client_info_dict is use to fill in the Last, First and Delivery Route when the guest_lists are generated
   #client_info_dict={'1': ['Cindy', 'Walsh', '04 - JSM'], '2': ['Linda', 'Webb', '20 - Quaker'],

   if not os.path.isfile(TEMPORARY_CLIENT_LIST_FILENAME):
      client_info_dict = get_client_lists(token)
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
      this_weeks_dates = ["2026-06-26", "2026-06-27"]
      print(f'Warning: using hardcoded dates: {this_weeks_dates}')
   else:
      Fridays_date = datetime.today() + datetime.timedelta(days=1)
      Saturdays_date = datetime.today() + datetime.timedelta(days=2)
      this_weeks_dates = [Fridays_date.strftime('%Y-%m-%d'), Saturdays_date.strftime('%Y-%m-%d')]

   # the four guest_lists enumerated by GUEST_LIST_IDX_E;  the array is created here and filled in by the function
   guest_lists = [[],[],[],[]]
   guest_lists = get_visits(token, guest_lists, this_weeks_dates, client_info_dict)

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
   for list_idx, guest_list in enumerate(guest_lists):
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
      
   write_report_pdf_file(guest_lists, status_strings, output_directory)

   text_report_path = os.path.join(output_directory, "make_tags_report.txt")
   with open(text_report_path, "w") as report_file:
      for line in status_strings:
         report_file.write(line + "\n")

