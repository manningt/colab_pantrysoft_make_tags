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
this_weeks_dates = ["2026-05-22", "2026-05-23"]
friday_split_report_hour = 15
# timeslots_dict = {
#    'Saturday': (7, 12),
#    'Friday-before-3': (12, 15),
#    'Friday-after-3': (15, 23)}

class PICKUP_LIST_IDX_E(enum.Enum): 
   Friday_before_3 = 0
   Friday_after_3 = 1
   Saturday = 2
   Delivery = 3

def get_visits():
   token = load_token()

   guest_list = [[],[],[],[]]

   page_number = 1
   record_limit = 2
   url = "https://app.pantrysoft.com/api/v1/visit/"
   params = {
      "page": page_number,
      "limit": record_limit,
      "sort": "visitDatetime",
      "order": "DESC",
      "aggregates": "false"
   }
   headers = {
      "accept": "application/json",
      "X-Auth-Token": token
   }

   response = requests.get(url, headers=headers, params=params)
   
   if response.status_code != 200:
      print(f"Request failed with status code {response.status_code}")
      print(response.text)
      exit()

   response_list = response.json()
   next_page = response_list['next_page']
   for visit_dict in response_list['data']:
      item_count = 0
      for item_dict in visit_dict['inventory_visit_items']:
         item_count += item_dict['quantity']
      if visit_dict['visit_type'] is 'Pickup':
         date_str, time_str = visit_dict['visit_datetime'].split(' ')
         client_tuple = (visit_dict['client_id'], None, time_str, item_count)
         guest_list_index = None
         if date_str == this_weeks_dates[FRIDAY_IDX]:
            if time_str[:2] < friday_split_report_hour:
               guest_list_index = PICKUP_LIST_IDX_E.Friday_before_3.value
            else:
               guest_list_index = PICKUP_LIST_IDX_E.Friday_after_3.value
         elif date_str == this_weeks_dates[SATURDAY_IDX]:
            guest_list_index = PICKUP_LIST_IDX_E.Saturday.value
         else:
            print(f"date out-of-range: {visit_dict['visit_datetime']=}  {visit_dict['id']=} {visit_dict['visit_type']=} {visit_dict['client_id']=}")
      elif visit_dict['visit_type'] is 'Delivery':
         # visit date_time is the delivery route
         client_tuple = (visit_dict['client_id'], None, visit_dict['visit_datetime'], item_count)
         guest_list_index = PICKUP_LIST_IDX_E.Delivery.value
      else:
         print(f"Unknown visit_type: {visit_dict['visit_type']=} {visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['client_id']=}")

      if guest_list_index:
         guest_list[guest_list_index].append(client_tuple)

      # print(f"{visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['visit_type']=} {visit_dict['client_id']=} {item_count=}")



if __name__ == "__main__":
    get_visits()
