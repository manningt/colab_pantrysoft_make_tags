
import os
import csv
from make_bag_tags_and_report import item_count_to_label_count

def write_csv(guest_list_list, output_directory, csv_base_filename, client_info):
   csv_path = os.path.join(output_directory, csv_base_filename)

   delivery_array = [['Bags', 'Labels', 'Items', 'First', 'Last', 'Route']]
   pickup_array   = [['Bags', 'Labels', 'Items', 'First', 'Last', 'Time']]

   for guest_list in guest_list_list:
      for visit_tuple in guest_list:
         # visit_tuple pickup:   client_id, item_count, time, last_name, first_name)
         # visit_tuple delivery: client_id, item_count, None, delivery_route, last_name)
         # client_info_dict[client_id] =[first, last, delivery_route, phone, street_address, unit_no, city]
         client_id = visit_tuple[0]
         first_name = client_info[client_id][0]
         last_name = client_info[client_id][1]
         item_count = int(visit_tuple[1])
         label_count = int(item_count_to_label_count(item_count))
         if visit_tuple[2] is not None:
            pickup_array.append(["",label_count,item_count,first_name,last_name,visit_tuple[2][:5]])
         else:
            delivery_array.append(["",label_count,item_count,first_name,last_name,visit_tuple[3]])

   csv_path = os.path.join(output_directory, "Deliveries" + csv_base_filename)
   with open(csv_path, 'w', newline='') as csvfile:
      writer = csv.writer(csvfile)
      writer.writerows(delivery_array)

   csv_path = os.path.join(output_directory, "Pickups" + csv_base_filename)
   with open(csv_path, 'w', newline='') as csvfile:
      writer = csv.writer(csvfile)
      writer.writerows(pickup_array)

   print(f'Done creating csv files: {len(pickup_array)-1} pickups; {len(delivery_array)-1} deliveries')