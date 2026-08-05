
import os
import json
import time as unix_time
import requests
from defines import FRIDAY_IDX, SATURDAY_IDX, FRIDAY_SPLIT_REPORT_HOUR, GUEST_LIST_IDX_E

def load_token(config_path):
   """Loads the X-Auth-Token from a configuration file."""
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

def parse_visit_response(response_data, guest_visit_lists, this_weeks_dates, client_info_dict):
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
         print(f"\nvisit has no items: {visit_dict['visit_type']=} {visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['client_id']=}")
         continue

      client_id = visit_dict['client_id']
      if client_id not in client_info_dict:
         print(f"\n{client_id=} not in client_info, so name lookup failed.")
         continue

      first_name = client_info_dict[client_id][0]
      last_name = client_info_dict[client_id][1]
      delivery_route = client_info_dict[client_id][2]

      # the client tuple includes the delivery route (or first name) and last_name for sorting
      if visit_dict['visit_type'] == 'Delivery':
         client_tuple = (visit_dict['client_id'], item_count, None, delivery_route, last_name)
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

         client_tuple = (visit_dict['client_id'], int(item_count), pickup_time_str, last_name, first_name)
         if date_str == this_weeks_dates[FRIDAY_IDX]:
            if pickup_hour < FRIDAY_SPLIT_REPORT_HOUR:
               guest_list_index = GUEST_LIST_IDX_E.Pickup_Friday_before_3.value
            else:
               guest_list_index = GUEST_LIST_IDX_E.Pickup_Friday_after_3.value
         elif date_str == this_weeks_dates[SATURDAY_IDX]:
            guest_list_index = GUEST_LIST_IDX_E.Pickup_Saturday.value
         else:
            # print(f"date out-of-range: {visit_dict['visit_datetime']=} {visit_dict['id']=} {visit_dict['visit_type']=} {visit_dict['client_id']=}")
            done = True
            # adjust the record count; the decreasing date limit has been hit and this record wasn't added
            record_count -= 1
            break
      else:
         print(f"Unknown visit_type: {visit_dict['visit_type']=} {visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['client_id']=}")

      if guest_list_index is not None:
         guest_visit_lists[guest_list_index].append(client_tuple)
         added_count += 1
      else:
         print(f"guest list index is None: {visit_dict['visit_type']=} {visit_dict['id']=} {visit_dict['visit_datetime']=} {visit_dict['client_id']=}")
   
   if record_count != added_count:
      print(f"Error: parse_visit_response added {added_count} visits but the {record_count=}; {done=}")
   return done, guest_visit_lists


def get_visits(token, this_weeks_dates, client_info_dict):
   # the list of lists is created here; the lists are appended to 
   guest_visit_lists = [[],[],[],[]]

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

      done, guest_visit_lists = parse_visit_response(response_list['data'], guest_visit_lists, this_weeks_dates, client_info_dict)
      print(' .', end='', flush=True)
      if 0: 
         print(f"{page_number=} list_lengths: ", end="")
         for guest_list_index in GUEST_LIST_IDX_E:
            print(f"{guest_list_index.name}={len(guest_visit_lists[guest_list_index.value])} ", end="")
         print()

      if done:
          break

   elapsed_time =  unix_time.time() - start_time
   average_time_per_page = page_number/elapsed_time
   for guest_list_index in GUEST_LIST_IDX_E:
      total_visits += len(guest_visit_lists[guest_list_index.value])
   print(f' done: {total_visits} visits retrieved in {elapsed_time:.2f} seconds; average_per_page={average_time_per_page:.2f}', flush=True)

   return guest_visit_lists

def parse_client_response(response_list, client_info_dict):
   record_count = 0
   added_count = 0
   for individual_client_dict in response_list:
      record_count += 1
      client_id = individual_client_dict['id']
      # if record_count == 1:
      #    print(f"DEBUG {individual_client_dict=}")

      if 'household_members' in individual_client_dict:
         # [0] is the first household member
         first = individual_client_dict['household_members'][0]['first_name']
         last = individual_client_dict['household_members'][0]['last_name']
         phone = individual_client_dict['household_members'][0]['phone']
         if not individual_client_dict['household_members'][0]['is_primary']:
            print(f"Warning: {first} {last} does not have is_primary set: {client_id=}")
      else:
         print(f"Error: {client_id=} has no household members")
         continue

      if 'delivery_route_name' in individual_client_dict:
         delivery_route = individual_client_dict['delivery_route_name']
      else:
         delivery_route = 'None'

      if 'street_address' in individual_client_dict:
         street_address = individual_client_dict['street_address']
      else:
         print(f"Warning: {first} {last} does not have a street address: {client_id=}")
         street_address = "No Street"

      if 'unit_no' in individual_client_dict:
         unit_no = individual_client_dict['unit_no']
      else:
         unit_no = ""

      if 'city' in individual_client_dict:
         city = individual_client_dict['city']
      else:
         print(f"Warning: {first} {last} does not have a city: {client_id=}")
         city = 'No City'
      
      added_count += 1
      client_info_dict[client_id] =[first, last, delivery_route, phone, street_address, unit_no, city]

   if record_count != added_count:
      print(f"Error: parse_client_response() added {added_count} but there were {record_count} records")
   return client_info_dict, added_count

def get_client_lists(token):
   # as of July 2026, there are about 800 active clients, aka guests
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
