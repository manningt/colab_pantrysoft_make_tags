#get_registration_data functions
import time as unix_time
import requests

'''
The following code was in generator.py to get a list of guests with landlines:
   Test registration GET:
      with open("my-priority.json", "r") as fp:
         clients_with_priority_list = json.load(fp)
      get_registrations(pantrysoft_token, clients_with_priority_list)

   Get the latest client registrations for all clients:
      make_priority_landline_lists(pantrysoft_token, client_info_dict)

   Make a list of all landline phone numbers:
      with open("my-landlines.json", "r") as fp:
         landline_client_info_dict = json.load(fp)
      for client_id in landline_client_info_dict:
         print(f"{client_info_dict[client_id][3]} {client_info_dict[client_id][1]} {client_info_dict[client_id][0]}")
'''


'''
currently used as a prototype for testing registration data
   inputs is the client_id_list - which is a dictionary of client_id's and client data items
   iterates through the client_list dictionary and gets the most recent registration data
   returns nothing
   prints out 2 lists: clients with priority, clients with landline.  These were copied into a json file

   1 run showed:
      the following client_id's without registration data:  818, 1186, 1236, 1258, 1321
      the following output for performance:
         done: 829 guest's registrations retrieved in 346.30 seconds; average_per_page=2.39
'''
def make_priority_landline_lists(token, client_info_dict):

   clients_with_priority = {}
   clients_with_landlines = {}

   # https://app.pantrysoft.com/api/v1/registration/?limit=1&sort=registrationDatetime&order=DESC&client_id=109'
   url = "https://app.pantrysoft.com/api/v1/registration/"
   params = {
      "client_id": 0,
      "limit": 1,
      "sort": "registrationDatetime",
      "order": "DESC",
   }
   headers = {
      "accept": "application/json",
      "X-Auth-Token": token
   }

   query_count = 0
   start_time = unix_time.time()
   # print('Fetching registrations per client', end='', flush=True)
   for client_id, value in client_info_dict.items():
      # print(f"{client=}")
      params["client_id"] = client_id
      response = requests.get(url, headers=headers, params=params)
      if response.status_code != 200:
         print(f"Request failed with status code {response.status_code}")
         print(response.text)
         exit()

      query_count += 1
      response_list = response.json()
      # print(f"{client[0]} {response_list['data'][0]['registration_questions']['Priority']}")
      try:
         questions = response_list['data'][0]['registration_questions']
      except:
         print(f"{client_id} does not have registration_questions; reponse was:")
         print(f"\t{response_list}")
         continue
      if 'Priority' in questions:
         has_priority = questions['Priority']
      else:
         has_priority = False

      if 'registration_cell' in questions:
         if questions['registration_cell'].lower() == "yes":
            is_landline = False
         else:
            is_landline = True
      else:
         print(f"{client_id} {value[0]} does not have registration_cell in questions, assuming cell")
         is_landline = False

      # print(f"{client_id} {value[0]} {value[1]} {has_priority=} {is_landline=}")
      if has_priority:
         clients_with_priority[client_id] = value[1]
         # break
      if is_landline:
         clients_with_landlines[client_id] = [value[1], value[0]]

      if query_count % 100 == 0:
         print(f'{query_count} queries; {len(clients_with_priority)=} {len(clients_with_landlines)=}')

      # client_info_dict, clients_added_count = parse_client_response(response_list['data'], client_info_dict)

      # print(' .', end='', flush=True)
   print(f'Priority: {len(clients_with_priority)}: {clients_with_priority}')
   print(f'/nLandlines: {len(clients_with_landlines)}: {clients_with_landlines}')
   elapsed_time = unix_time.time() - start_time
   average_time_per_page = query_count/elapsed_time
   print(f" done: {query_count} guest's registrations retrieved in {elapsed_time:.2f} seconds; average_per_page={average_time_per_page:.2f}", flush=True)

   return clients_with_priority, clients_with_landlines

'''
currently used as a prototype for testing registration data
   inputs are a list of tuples with last_name, client_id.  The last_name is just for print outs
      exmaple priority_list = [["Kriajeva", 370], ["Reynoso", 109], ["Mirzayee", 401]]
   returns nothing
   prints out whether a client has a landline and/or priority
'''
def get_registrations(token, priority_list):
   
   # https://app.pantrysoft.com/api/v1/registration/?limit=1&sort=registrationDatetime&order=DESC&client_id=109'
   url = "https://app.pantrysoft.com/api/v1/registration/"
   params = {
      "client_id": 0,
      "limit": 1,
      "sort": "registrationDatetime",
      "order": "DESC",
   }
   headers = {
      "accept": "application/json",
      "X-Auth-Token": token
   }

   start_time = unix_time.time()
   # print('Fetching registrations per client', end='', flush=True)
   for client in priority_list:
      params["client_id"] = client[1]
      response = requests.get(url, headers=headers, params=params)
      if response.status_code != 200:
         print(f"Request failed with status code {response.status_code}")
         print(response.text)
         exit()

      response_list = response.json()
      # print(f"{client[0]} {response_list['data'][0]['registration_questions']['Priority']}")
      questions = response_list['data'][0]['registration_questions']
      if 'Priority' in questions:
         has_priority = questions['Priority']
      else:
         has_priority = False

      if 'registration_cell' in questions:
         if questions['registration_cell'].lower() == "yes":
            is_landline = False
         else:
            is_landline = True
      else:
         print(f"{client[0]} id={client[1]} does not have registration_cell in questions, assuming cell")
         is_landline = False

      print(f"{client[0]} id={client[1]} {has_priority=} {is_landline=}")

      # print(' .', end='', flush=True)
      elapsed_time = unix_time.time() - start_time
      average_time_per_page = len(priority_list)/elapsed_time
      # print(f' done: {len(client_info_dict)} active guests retrieved in {elapsed_time:.2f} seconds; average_per_page={average_time_per_page:.2f}', flush=True)

   return