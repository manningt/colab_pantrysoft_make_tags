
import os
import csv

def write_delivery_tally_csv(guest_list, output_directory, csv_filename):

   routes_dict = {}
   total_deliveries_count = 0
   for visit_tuple in guest_list:
      visit_route = visit_tuple[3].replace("- ", ": ").replace(" :", ":")
      visit_route = visit_route.replace(",", "-") #remove commas in routes to avoid putting name in quotes when writing CSV
      if visit_route not in routes_dict:
         routes_dict[visit_route] = 1
      else:
         routes_dict[visit_route] += 1
      total_deliveries_count += 1

   routes_list = list(routes_dict.items())
   routes_list.sort()
   routes_list.insert(0, ['Route', 'Count'])
   routes_list.append(['Total', total_deliveries_count])

   csv_path = os.path.join(output_directory, csv_filename)
   with open(csv_path, 'w', newline='') as csvfile:
      writer = csv.writer(csvfile)
      writer.writerows(routes_list)

   print(f'Done creating {csv_filename}; total deliveries = {total_deliveries_count}')