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
        tuples with the guest's first name, last name, route or pickup time, and item count.

make 4 interim lists, where the list is a tuple: clientID, none, route or pickup time, and item count.
   then go and replace ClientID with first name, and None with Last Name

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
friday_split_report_hour = 15

class GUEST_LIST_IDX_E(enum.Enum): 
   Friday_before_3 = 0
   Friday_after_3 = 1
   Saturday = 2
   Delivery = 3

def parse_visit_response(response_data, guest_lists, this_weeks_dates):
   done = False #only True when we hit a date out of range
   for visit_dict in response_data:
      item_count = 0
      for item_dict in visit_dict['inventory_visit_items']:
         item_count += item_dict['quantity']
      # print(f"{visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['visit_type']=} {visit_dict['client_id']=} {item_count=}")

      guest_list_index = None
      if visit_dict['visit_type'] == 'Delivery':
         # visit date_time is the delivery route
         client_tuple = (visit_dict['client_id'], None, visit_dict['visit_datetime'], item_count)
         guest_list_index = GUEST_LIST_IDX_E.Delivery.value
      elif visit_dict['visit_type'] == 'Pickup':
         date_str, time_str = visit_dict['visit_datetime'].split(' ')
         client_tuple = (visit_dict['client_id'], None, time_str, item_count)
         if date_str == this_weeks_dates[FRIDAY_IDX]:
            try:
               pickup_hour = int(time_str[:2])
            except ValueError:
               print(f"time string not an integer: {visit_dict['visit_datetime']=} {visit_dict['id']=} {visit_dict['visit_type']=} {visit_dict['client_id']=}")
               exit()

            if pickup_hour < friday_split_report_hour:
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

      if guest_list_index:
         guest_lists[guest_list_index].append(client_tuple)

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
      # print(f"{next_page=}")

      done, guest_lists = parse_visit_response(response_list['data'], guest_lists, this_weeks_dates)
      if 1: 
         print(f"{page_number=} {done=} list_lengths: ", end="")
         for guest_list_index in GUEST_LIST_IDX_E:
            print(f"{guest_list_index.name}={len(guest_lists[guest_list_index.value])} ", end="")
         print()
      if done:
         break

   return guest_lists

if __name__ == "__main__":
   token = load_token()
   this_weeks_dates = ["2026-05-22", "2026-05-23"]
   guest_lists = [[],[],[],[]]
   guest_lists = get_visits(guest_lists, this_weeks_dates, token)

   if True:
      for list_idx, guest_list in enumerate(guest_lists):
         # guest_list.sort(key=lambda x: (x[2], x[0]))
         print(f"{GUEST_LIST_IDX_E(list_idx).name}")
         for idx, guest in enumerate(guest_list):
            print(f"\t{idx} {guest}")
