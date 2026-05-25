#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "requests"
# ]
# ///
'''
the 4 lists are: 
  Delivery, 'Saturday': (7, 12), 'Friday-before-3': (12, 15), 'Friday-after-3': (15, 23)}
      where each list is:
        tuples with the guest's first name, last name, route or pickup time, and item count

make 4 interim lists, where the list is a tuple: clientID, none, route or pickup time, and item count.
   then go and replace ClientID with first name, and None with Last Name, e.g.
      guest_list.append((row['First'], row['Last'], row['Route or Pickup Time'], item_count))

'''
from datetime import time
import os
import json
import requests
import enum

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
FRIDAY_SPLIT_REPORT_HOUR = 3

class GUEST_LIST_IDX_E(enum.Enum): 
   Friday_before_3 = 0
   Friday_after_3 = 1
   Saturday = 2
   Delivery = 3

def parse_visit_response(response_data, guest_lists, this_weeks_dates):
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

      if item_count == 0:
         print(f"visit has no items: {visit_dict['visit_type']=} {visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['client_id']=}")
         continue

      if visit_dict['visit_type'] == 'Delivery':
         # the delivery route (3rd parameter) is grabbed later using the client_id
         client_tuple = (visit_dict['client_id'], None, None, item_count)
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

         client_tuple = (visit_dict['client_id'], None, pickup_time_str, item_count)
         if date_str == this_weeks_dates[FRIDAY_IDX]:
            if pickup_hour < FRIDAY_SPLIT_REPORT_HOUR:
               guest_list_index = GUEST_LIST_IDX_E.Friday_before_3.value
            else:
               guest_list_index = GUEST_LIST_IDX_E.Friday_after_3.value
         elif date_str == this_weeks_dates[SATURDAY_IDX]:
            guest_list_index = GUEST_LIST_IDX_E.Saturday.value
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

   if record_count != added_count:
      print(f"parse visits results {record_count=} {added_count=} {done=}")
   return done, guest_lists

def get_visits(guest_lists, this_weeks_dates, token):

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

   for page_number in range(1, MAX_PAGE_NUMBER):
      params["page"] = page_number
      response = requests.get(url, headers=headers, params=params)
      if response.status_code != 200:
         print(f"Request failed with status code {response.status_code}")
         print(response.text)
         exit()

      response_list = response.json()
      # next_page = response_list['next_page']

      done, guest_lists = parse_visit_response(response_list['data'], guest_lists, this_weeks_dates)
      if 1: 
         print(f"{page_number=} list_lengths: ", end="")
         for guest_list_index in GUEST_LIST_IDX_E:
            print(f"{guest_list_index.name}={len(guest_lists[guest_list_index.value])} ", end="")
         print()
      if done:
         break

   return guest_lists

def parse_client_response(response_list, client_info_dict):
   record_count = 0
   added_count = 0
   for individual_client_dict in response_list:
      record_count += 1
      client_id = individual_client_dict['id']
      if record_count == 1:
         print(f"DEBUG {individual_client_dict=}")

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
      print(f"parse clients results {record_count=} {added_count=}")
   return client_info_dict

def get_client_lists(token, client_info_dict):
   RECORD_LIMIT = 5
   MAX_PAGE_NUMBER = 2

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

   for page_number in range(1, MAX_PAGE_NUMBER):
      params["page"] = page_number
      response = requests.get(url, headers=headers, params=params)
      if response.status_code != 200:
         print(f"Request failed with status code {response.status_code}")
         print(response.text)
         exit()

      response_list = response.json()
      client_info_dict = parse_client_response(response_list['data'], client_info_dict)

   return client_info_dict

if __name__ == "__main__":
   token = load_token()

   client_info_dict = {}
   client_info_dict = get_client_lists(token, client_info_dict)
   print(f"DONE: {client_info_dict=}")
   exit()

   this_weeks_dates = ["2026-05-22", "2026-05-23"]
   guest_lists = [[],[],[],[]]
   guest_lists = get_visits(guest_lists, this_weeks_dates, token)

   PRINT_LISTS = True
   if PRINT_LISTS:
      for list_idx, guest_list in enumerate(guest_lists):
         # guest_list.sort(key=lambda x: (x[2], x[0]))
         print(f"{GUEST_LIST_IDX_E(list_idx).name}")
         for idx, guest in enumerate(guest_list):
            print(f"\t{idx} {guest}")
