import os
from fpdf import FPDF
import copy

from defines import DELIVERY_TYPE, GUEST_LIST_IDX_E, AM_PM_TYPE
import datetime

def item_count_to_label_count(item_count):
   limits = [0, 9, 17, 25, 32, 40, 49,57,67,73,82,90,100,107,112,139,200]
   if item_count > 200:
      return 16
   for i in range(len(limits)-1):
      if item_count > limits[i] and item_count <= limits[i+1]:
         # increase small bag counts on odd week numbers
         if i < 4 and (datetime.datetime.today().isocalendar()[1] % 2):
            return i + 2
         else:
            return i + 1

def make_label_pdfs(guest_list, type, pdf_filename, output_directory, client_info):
   # PDF writing examples:
   #  https://medium.com/@mahijain9211/creating-a-python-class-for-generating-pdf-tables-from-a-pandas-dataframe-using-fpdf2-c0eb4b88355c
   #  https://py-pdf.github.io/fpdf2/Tutorial.html
   route_font_size = 28 # allows longer names
   name_font_size = 36
   label_count_font_size = 12
   label_height = 144 #points
   label_width = 288
   number_of_labels = 0
   cell_width = 0
   cell_height = 0

   if len(guest_list) == 0:
      status_string = f"Failure: no guests in the guest_list to generate {pdf_filename}."
   else:
      try:
         pdf = FPDF(orientation="L", unit="pt", format=(label_height,label_width))
      except Exception as e:
         status_string = f"Failure: could not create PDF for {pdf_filename} exception: {e}"
         return status_string
      
      try:
         pdf.set_margins(0, 18, 0) #left, top, right in points
         pdf.set_auto_page_break(auto=False)
         pdf.set_font("Helvetica", "B") # Arial not available in fpdf2
         for visit_tuple in guest_list:
            label_count = int(item_count_to_label_count(visit_tuple[1]))
            # client_info_dict[client_id] =[first, last, delivery_route, phone, street_address, unit_no, city]
            client_id = visit_tuple[0]
            first_name = client_info[client_id][0]
            last_name = client_info[client_id][1]
            # print(f"  {row[0]} {row[1]} {row[2]} has {row[3]} items, which is {label_count} labels.")
            for i in range(label_count):
               pdf.add_page()
               # if row[2] is a time, then don't print it; only print if it's a route
               if type == DELIVERY_TYPE:
                  pdf.set_font_size(route_font_size)
                  delivery_route = client_info[client_id][2].replace(" - ", ": ")
                  pdf.cell(cell_width, cell_height, delivery_route, align="L")
                  pdf.line(0, 36, label_width, 36) # line from left to right
               pdf.ln(route_font_size+10)
               pdf.set_font_size(name_font_size)
               pdf.cell(cell_width, cell_height, f"{first_name.title()}", align="C")
               pdf.ln(name_font_size+4)
               pdf.cell(cell_width, cell_height, f"{last_name[0:15].title()}", align="C")
               pdf.ln(name_font_size+4)
               pdf.set_font_size(label_count_font_size)
               pdf.cell(cell_width, cell_height, f"{i+1} of {label_count}", align="R")
               number_of_labels += 1
      except Exception as e:
         status_string = f"Failure: while adding cells for {pdf_filename} exception: {e}"
         return status_string
      
      try:
         out_pdf_path = os.path.join(output_directory, pdf_filename)
         pdf.output(out_pdf_path)
         status_string = f"{pdf_filename} has {len(guest_list)} guests and {number_of_labels} labels."
      except Exception as e:
         #    current_app.logger.warning(f"PDF for {guest} failed: {e}")
         status_string = f"failed to generate {pdf_filename} exception: {e}"

   return status_string

'''  used for testing:
def write_report_file(guest_list, report_filename, output_directory):
   text_report_filename = report_filename.replace('.pdf', '.txt')
   text_report_path = os.path.join(output_directory, text_report_filename)
   try:
      with open(text_report_path, "w") as f:
         f.write(f"\n{text_report_filename}\n")
         # f.write(f"  First       Last     Time/Route     Items\n")
         for guest in guest_list:
            f.write(f"{guest[0]:<12} {guest[1]:<12}   {guest[2]:<20}   Items={guest[3]}\n")
   except Exception as e:
      print(f"Failed to write report file {report_filename}: {e}")  
'''

def write_tag_report_pdf(guest_list_list,  status_list, output_directory, tag_pdf_report_filename, client_info):
   if len(guest_list_list) == 0:
      print("Failure: no guest lists in request to generate PDF report on tag files.")
      return False
   
   pdf_report_path = os.path.join(output_directory, tag_pdf_report_filename)
   try:
      pdf = FPDF(orientation="portrait", unit="pt", format="letter")
   except Exception as e:
      print(f"Failure: could not create PDF for {pdf_report_path} exception: {e}")
      return False
   
   #72 points = 1 inch;   42 rows fit on a page   
   pdf.set_margins(12, 24, 12) #left, top, right in points
   center_spacer_width = 52
   widths = (64, 90, 54, 36, center_spacer_width, 64, 90, 54, 36)
   number_of_rows_on_a_page = 42

   # print(f"\nGenerating {pdf_report_path}: {len(guest_list_list)} guest lists. {status_list=}")
   for g_l_index in range(len(guest_list_list)):
      if 'Delivery' in status_list[g_l_index]:
         column_title = 'Route'
      else:
         column_title = 'Time'

      current_row = 0
      guest_list_page_number = 0
      page_count = (len(guest_list_list[g_l_index]) // (number_of_rows_on_a_page * 2)) + 1
      # print(f"\t{g_l_index=} {status_list[g_l_index]} has {len(guest_list_list[g_l_index])} guests.")
      try:
         while current_row < len(guest_list_list[g_l_index]):
            pdf.add_page()
            guest_list_page_number += 1
            pdf.set_font("Helvetica", "B")
            pdf.cell(0,0, f'{status_list[g_l_index]}      Page {guest_list_page_number} of {page_count}', align="L")
            pdf.ln(pdf.font_size+4)
            pdf.set_font("Helvetica", "", size=12)
            with pdf.table(line_height=pdf.font_size, padding=2, width=sum(widths), col_widths=widths) as table:
               row = table.row()
               # header row
               row.cell("First")
               row.cell("Last")
               row.cell(column_title)
               row.cell("Items")
               row.cell("", border=0) # spacer
               if len(guest_list_list[g_l_index]) > number_of_rows_on_a_page:
                  # only make second column if there is enough data
                  row.cell("First")
                  row.cell("Last")
                  row.cell(column_title)
                  row.cell("Items")
               else:
                  for _ in range(4):
                     row.cell("", border=0)
               # make dual data columns
               for _ in range(number_of_rows_on_a_page):
                  row = table.row()
                  client_id = guest_list_list[g_l_index][current_row][0]
                  item_count = guest_list_list[g_l_index][current_row][1]
                  if column_title == 'Time':
                     time_or_route = guest_list_list[g_l_index][current_row][2]
                     last_name_index = 3
                  else:
                     time_or_route = client_info[client_id][2].replace(" - ", ": ")
                     last_name_index = 4
                  first_name = client_info[client_id][0].title()
                  # use last name with asterisk instead of: client_info[client_id][1]
                  last_name = guest_list_list[g_l_index][current_row][last_name_index].title()
                  # first column
                  row.cell(first_name[:8])
                  row.cell(last_name[:14])
                  row.cell(time_or_route[:7])
                  row.cell(str(item_count)[:3])
                  row.cell("", border=0)
                  # second column
                  index = current_row + number_of_rows_on_a_page
                  if index < len(guest_list_list[g_l_index]):
                     client_id = guest_list_list[g_l_index][index][0]
                     item_count = guest_list_list[g_l_index][index][1]
                     if column_title == 'Time':
                        time_or_route = guest_list_list[g_l_index][index][2]
                        last_name_index = 3
                     else:
                        time_or_route = client_info[client_id][2].replace(" - ", ": ")
                        last_name_index = 4
                     first_name = client_info[client_id][0].title()
                     last_name = guest_list_list[g_l_index][index][last_name_index].title()
                     row.cell(first_name[:8])
                     row.cell(last_name[:14])
                     row.cell(time_or_route[:7])
                     row.cell(str(item_count)[:3])
                     # print(f"\t\t{current_row=} {last_name=} {first_name=} {time_or_route=}")
                  else:
                     for _ in range(4):
                        row.cell("", border=0)
                  current_row += 1
                  if current_row >= len(guest_list_list[g_l_index]):
                     # print(f"\t  End of guest list reached at {current_row=}.")
                     break
            current_row += number_of_rows_on_a_page # skip to next set of rows
               
      except Exception as e:
         status_string = f"Failure: while making table for {pdf_report_path} exception: {e}"
         return status_string
      
   try:
      pdf.output(pdf_report_path)
      # status_string = f"{pdf_report_path} has {len(guest_list)} guests."
   except Exception as e:
      #    current_app.logger.warning(f"PDF for {guest} failed: {e}")
      print(f"failed to generate {pdf_report_path} exception: {e}")
      return False
   return True

def normalize_phone_number(number):
   import re
   clean_number = re.sub("[^0-9]", "", str(number))
   if len(clean_number) != 10:
      print(f"bad phone number: {clean_number}")
   return f'{clean_number[:3]}.{clean_number[3:6]}.{clean_number[6:]}'

def write_expeditor_2column_pdf(guest_list_list, output_directory, expeditor_pdf_filename, client_info, this_weeks_date):
   if len(guest_list_list) == 0:
      print("Failure: no guest lists in request to generate PDF report on tag files.")
      return False

   pdf_report_path = os.path.join(output_directory, f'{expeditor_pdf_filename}')
   try:
      pdf = FPDF(orientation="portrait", unit="pt", format="letter")
   except Exception as e:
      print(f"Failure: could not create PDF for {pdf_report_path} exception: {e}")
      return False

   side_margins = 8
   pdf.set_margins(side_margins, 24, side_margins) #left, top, right in points
   printable_pixels = (8.5*72)-(2*side_margins)
   #72 points = 1 inch;  page minus margins is 596 pixels wide
   number_of_rows_on_a_page = 20
   center_spacer_width = 20
   header = ["Bag", "Time", "First", "Last", "Phone"]
   bag_width = 30
   route_time_width = 38
   first_name_width = 60
   last_name_width = 72
   phone_width = 78
   widths = (bag_width, route_time_width, first_name_width, last_name_width, phone_width, \
      center_spacer_width, bag_width, route_time_width, first_name_width, last_name_width, phone_width)
   # print(f"there are {len(widths)} columns with a total width of {sum(widths)} pixels; should not exceed {printable_pixels} pixels")

   # print(f"\nGenerating {pdf_report_path}: {len(guest_list_list)} guest lists.")
   for g_l_index in range(len(guest_list_list)):
      if "deliv" in expeditor_pdf_filename.lower():
         if g_l_index == GUEST_LIST_IDX_E.Delivery.value:
            header[1] = "Route"
            is_delivery = True
         else:
            continue
      elif g_l_index != GUEST_LIST_IDX_E.Delivery.value:
         is_delivery = False
      else:
         continue

      current_row = 0
      guest_list_page_number = 0
      page_count = (len(guest_list_list[g_l_index]) // (number_of_rows_on_a_page * 2)) + 1
      # print(f"\t{g_l_index=} {GUEST_LIST_IDX_E(g_l_index).name} has {len(guest_list_list[g_l_index])} guests; will generate {page_count} pages")
      try:
         while current_row < len(guest_list_list[g_l_index]):
            pdf.add_page()
            guest_list_page_number += 1
            pdf.set_font("Helvetica", "B", size=11)
            if g_l_index == GUEST_LIST_IDX_E.Pickup_Saturday.value:
               date_str = this_weeks_date[1][-4:]
            else:
               date_str = this_weeks_date[0][-4:]
            pdf.cell(0,0, f'{GUEST_LIST_IDX_E(g_l_index).name} for {date_str}       Page {guest_list_page_number} of {page_count}', align="C")
            pdf.ln(pdf.font_size+4)
            pdf.set_font("Helvetica", "", size=12)

            with pdf.table(line_height=24, padding=1, width=sum(widths), col_widths=widths) as table:
               pdf_table_row = table.row()
               # header row
               for column_title in header:
                  pdf_table_row.cell(column_title)
               if len(guest_list_list[g_l_index]) > number_of_rows_on_a_page:
                  # only make second column if there is enough data
                  pdf_table_row.cell("", border=0) # spacer
                  for column_title in header:
                     pdf_table_row.cell(column_title)
               else:
                  for _ in range(len(header)):
                     pdf_table_row.cell("", border=0)

               # make dual data columns
               for _ in range(number_of_rows_on_a_page):
                  pdf_table_row = table.row()
                  # first column
                  # bags, route/time, first, last, phone, street, city
                  # item_count = guest_list_list[g_l_index][current_row][1]
                  # bags = str(item_count_to_label_count(item_count))
                  client_id = guest_list_list[g_l_index][current_row][0]
                  if is_delivery:
                     pickup_time = guest_list_list[g_l_index][current_row][3].replace(' - ',"\n")[:9]
                  else:
                     pickup_time = guest_list_list[g_l_index][current_row][2][:5]
                  # using the first name from the guest_list instead of the client because it maybe modified to the delivery_route
                  first_name = guest_list_list[g_l_index][current_row][4][:8] #client_info[client_id][0].title()[:8]
                  last_name = client_info[client_id][1].title()[:16]
                  phone = normalize_phone_number(client_info[client_id][3])
                  # first column
                  pdf_table_row.cell("") #bags, align="R")
                  if not is_delivery:
                     pdf.set_font("Helvetica", "", size=14)
                  pdf_table_row.cell(pickup_time)
                  pdf.set_font("Helvetica", "", size=12)
                  pdf_table_row.cell(first_name)
                  pdf.set_font("Helvetica", "", size=14)
                  pdf_table_row.cell(last_name)
                  pdf.set_font("Helvetica", "", size=12)
                  pdf_table_row.cell(phone)
                  # second column
                  index = current_row + number_of_rows_on_a_page
                  if index < len(guest_list_list[g_l_index]):
                     # item_count = guest_list_list[g_l_index][index][1]
                     # bags = str(item_count_to_label_count(item_count))
                     client_id = guest_list_list[g_l_index][index][0]
                     if is_delivery:
                        pickup_time = guest_list_list[g_l_index][current_row][3].replace(' - ',"\n")[:9]
                     else:
                        pickup_time = guest_list_list[g_l_index][index][2][:5]
                     first_name = guest_list_list[g_l_index][index][4][:8] #client_info[client_id][0].title()[:8]
                     last_name = client_info[client_id][1].title()[:16]
                     phone = normalize_phone_number(client_info[client_id][3])
                     pdf_table_row.cell("", border=0) #center spacer
                     pdf_table_row.cell("") #bags, align="R")
                     if not is_delivery:
                        pdf.set_font("Helvetica", "", size=14)
                     pdf_table_row.cell(pickup_time)
                     pdf.set_font("Helvetica", "", size=12)
                     pdf_table_row.cell(first_name)
                     pdf.set_font("Helvetica", "", size=14)
                     pdf_table_row.cell(last_name)
                     pdf.set_font("Helvetica", "", size=12)
                     pdf_table_row.cell(phone)
                     # print(f"\t\t{index=} {current_row=} {first_name} {last_name}")
                  else:
                     for _ in range(len(header)):
                        pdf_table_row.cell("", border=0)   
                  current_row += 1
                  if current_row >= len(guest_list_list[g_l_index]):
                     # print(f"\t  End of guest list reached at {current_row=}.")
                     break
            current_row += number_of_rows_on_a_page # skip to next set of rows
               
      except Exception as e:
         status_string = f"Failure: while making table for {pdf_report_path} exception: {e}"
         print(status_string)
         return status_string
      
   try:
      pdf.output(pdf_report_path)
   except Exception as e:
      #    current_app.logger.warning(f"PDF for {guest} failed: {e}")
      print(f"failed to generate {pdf_report_path} exception: {e}")
      return False
   return True

def move_delivery_to_pickup(guest_list_list, route_time_tuple_list):
   # the route_time_tuple specifies which route to match, and what time the pickup is to be
   # it then returns a modified guest_list_list with the matched route moved to a pickup time

   mod_guest_list_list = copy.deepcopy(guest_list_list)

   route_to_pickup_guest_list_list = [[],[],[],[]]

   list_of_deliveries_to_delete = []
   for list_idx, visit in enumerate(mod_guest_list_list[GUEST_LIST_IDX_E.Delivery.value]):
      for route_tuple in route_time_tuple_list:
         # test if route of visit is equal to one of the 
         if route_tuple[0] in visit[3]:
            # client ID, items, pickup time, last, first
            # it appears that deepcopy coverts the visit from an array to a tuple - so make an array:
            moved_visit = [visit[0], visit[1], route_tuple[1], visit[4], visit[3][5:]]
            pickup_hour = int(route_tuple[1][:2])
            if pickup_hour < 3:
               append_list_idx = GUEST_LIST_IDX_E.Pickup_Friday_before_3.value              
            elif pickup_hour < 8:
               append_list_idx = GUEST_LIST_IDX_E.Pickup_Friday_after_3.value              
            else:
               append_list_idx = GUEST_LIST_IDX_E.Pickup_Saturday.value              
            route_to_pickup_guest_list_list[append_list_idx].append(moved_visit)
            # print(f'{list_idx=} {visit=} -> {moved_visit=}')
            list_of_deliveries_to_delete.append(list_idx)

   for g_l_index in range(len(guest_list_list)):
      if len(route_to_pickup_guest_list_list[g_l_index]) > 0:
         mod_guest_list_list[g_l_index].extend(route_to_pickup_guest_list_list[g_l_index])

   for visit_idx in reversed(list_of_deliveries_to_delete):
      del mod_guest_list_list[GUEST_LIST_IDX_E.Delivery.value][visit_idx]

   if 0:
      for g_l_index in range(len(guest_list_list)):
         print(f'{GUEST_LIST_IDX_E(g_l_index).name} {len(guest_list_list[g_l_index])=} => {len(mod_guest_list_list[g_l_index])}')

   return mod_guest_list_list


def write_expeditor_1column_pdf(guest_list_list, output_directory, expeditor_pdf_filename, client_info, this_weeks_date):
   if len(guest_list_list) == 0:
      print("Failure: no guest lists in request to generate PDF report on tag files.")
      return False

   pdf_report_path = os.path.join(output_directory, f'{expeditor_pdf_filename}')
   try:
      pdf = FPDF(orientation="portrait", unit="pt", format="letter")
   except Exception as e:
      print(f"Failure: could not create PDF for {pdf_report_path} exception: {e}")
      return False

   side_margins = 8
   pdf.set_margins(side_margins, 24, side_margins) #left, top, right in points
   printable_pixels = (8.5*72)-(2*side_margins)
   #72 points = 1 inch;  page minus margins is 596 pixels wide
   number_of_rows_on_a_page = 24
   header = ["Bag", "Time", "First", "Last", "Phone"]
   bag_width = 30
   route_time_width = 220
   first_name_width = 72
   last_name_width = 84
   phone_width = 90
   widths = (bag_width, route_time_width, first_name_width, last_name_width, phone_width)
   # print(f"there are {len(widths)} columns with a total width of {sum(widths)} pixels; should not exceed {printable_pixels} pixels")

   # print(f"\nGenerating {pdf_report_path}: {len(guest_list_list)} guest lists.")
   for g_l_index in range(len(guest_list_list)):
      if "deliv" in expeditor_pdf_filename.lower():
         if g_l_index == GUEST_LIST_IDX_E.Delivery.value:
            header[1] = "Route"
            is_delivery = True
         else:
            continue
      elif g_l_index != GUEST_LIST_IDX_E.Delivery.value:
         is_delivery = False
      else:
         continue

      current_row = 0
      guest_list_page_number = 0
      page_count = (len(guest_list_list[g_l_index]) // (number_of_rows_on_a_page)) + 1
      # print(f"\t{g_l_index=} {GUEST_LIST_IDX_E(g_l_index).name} has {len(guest_list_list[g_l_index])} guests; will generate {page_count} pages")
      try:
         while current_row < len(guest_list_list[g_l_index]):
            pdf.add_page()
            guest_list_page_number += 1
            pdf.set_font("Helvetica", "B", size=11)
            if g_l_index == GUEST_LIST_IDX_E.Pickup_Saturday.value:
               date_str = this_weeks_date[1][-4:]
            else:
               date_str = this_weeks_date[0][-4:]
            pdf.cell(0,0, f'{GUEST_LIST_IDX_E(g_l_index).name} for {date_str}       Page {guest_list_page_number} of {page_count}', align="C")
            pdf.ln(pdf.font_size+4)
            pdf.set_font("Helvetica", "", size=12)

            with pdf.table(line_height=24, padding=1, width=sum(widths), col_widths=widths) as table:
               pdf.set_font("Helvetica", "", size=14)
               pdf_table_row = table.row()
               # header row
               for column_title in header:
                  pdf_table_row.cell(column_title)
 
               for _ in range(number_of_rows_on_a_page):
                  pdf_table_row = table.row()
                  # first column
                  # bags, route/time, first, last, phone, street, city
                  # item_count = guest_list_list[g_l_index][current_row][1]
                  # bags = str(item_count_to_label_count(item_count))
                  client_id = guest_list_list[g_l_index][current_row][0]
                  if is_delivery:
                     route_pickup_time = guest_list_list[g_l_index][current_row][3].replace("   "," ")
                     route_pickup_time = route_pickup_time.replace("  "," ").replace(" - ",": ")[:28]
                  else:
                     route_pickup_time = guest_list_list[g_l_index][current_row][2][:5]
                  # using the first name from the guest_list instead of the client because it maybe modified to the delivery_route
                  first_name = client_info[client_id][0].title()[:8]
                  # last_name = client_info[client_id][1].title()[:16]
                  last_name = guest_list_list[g_l_index][current_row][4].title()
                  phone = normalize_phone_number(client_info[client_id][3])
                  # first column
                  pdf_table_row.cell("") #bags, align="R")
                  pdf_table_row.cell(route_pickup_time)
                  pdf_table_row.cell(first_name)
                  pdf_table_row.cell(last_name)
                  pdf_table_row.cell(phone)
                  current_row += 1
                  if current_row >= len(guest_list_list[g_l_index]):
                     # print(f"\t  End of guest list reached at {current_row=}.")
                     break
               
      except Exception as e:
         status_string = f"Failure: while making table for {pdf_report_path} exception: {e}"
         print(status_string)
         return status_string
      
   try:
      pdf.output(pdf_report_path)
   except Exception as e:
      #    current_app.logger.warning(f"PDF for {guest} failed: {e}")
      print(f"failed to generate {pdf_report_path} exception: {e}")
      return False
   return True


def write_delivery_routes_pdf(guest_list_list, output_directory, expeditor_pdf_filename, client_info, this_weeks_date, routes_to_print):
   if len(guest_list_list) == 0:
      print("Failure: no guest lists in request to generate PDF report on tag files.")
      return False

   pdf_report_path = os.path.join(output_directory, f'{expeditor_pdf_filename}')
   try:
      pdf = FPDF(orientation="portrait", unit="pt", format="letter")
   except Exception as e:
      print(f"Failure: could not create PDF for {pdf_report_path} exception: {e}")
      return False

   side_margins = 8
   pdf.set_margins(side_margins, 24, side_margins) #left, top, right in points
   printable_pixels = (8.5*72)-(2*side_margins)
   #72 points = 1 inch;  page minus margins is 596 pixels wide
   number_of_rows_on_a_page = 16
   header = ["Bag", "First", "Last", "Street", "Unit", "Phone"]
   bag_width = 30
   first_name_width = 72
   last_name_width = 84
   street_width = 160
   unit_width = 100
   phone_width = 90
   widths = (bag_width, first_name_width, last_name_width, street_width, unit_width, phone_width)
   # print(f"there are {len(widths)} columns with a total width of {sum(widths)} pixels; should not exceed {printable_pixels} pixels")

   # print(f"\nGenerating {pdf_report_path}: {len(guest_list_list)} guest lists.")
   for g_l_index in range(len(guest_list_list)):
      if g_l_index != GUEST_LIST_IDX_E.Delivery.value:
         continue

      current_row = 0
      guest_list_page_number = 0
      # page_count = (len(guest_list_list[g_l_index]) // (number_of_rows_on_a_page)) + 1
      # print(f"\t{g_l_index=} {GUEST_LIST_IDX_E(g_l_index).name} has {len(guest_list_list[g_l_index])} guests; will generate {page_count} pages")
      current_route = "XX"
      route_guest_count = 0
      try:
         while current_row < len(guest_list_list[g_l_index]):
            this_route = guest_list_list[g_l_index][current_row][3]
            if this_route[:2] in routes_to_print and this_route[:2] != current_route[:2]:
               current_route = this_route
               pdf.add_page()
               guest_list_page_number += 1
               pdf.set_font("Helvetica", "B", size=11)
               date_str = this_weeks_date[0][-4:]
               pdf.cell(0,0, f'{this_route} for {date_str}       Page {guest_list_page_number}', align="C")
               pdf.ln(pdf.font_size+4)
               pdf.set_font("Helvetica", "", size=12)

               with pdf.table(line_height=24, padding=1, width=sum(widths), col_widths=widths) as table:
                  pdf.set_font("Helvetica", "", size=14)
                  pdf_table_row = table.row()
                  for column_title in header:
                     pdf_table_row.cell(column_title)

                  for _ in range(number_of_rows_on_a_page):
                     pdf_table_row = table.row()
                     client_id = guest_list_list[g_l_index][current_row][0]
                     first_name = client_info[client_id][0].title()[:8]
                     last_name = client_info[client_id][1].title()[:16]
                     street = client_info[client_id][4]             
                     unit = client_info[client_id][5]            
                     phone = normalize_phone_number(client_info[client_id][3])

                     pdf_table_row.cell("") #bags, align="R")
                     pdf_table_row.cell(first_name)
                     pdf_table_row.cell(last_name)
                     pdf_table_row.cell(street)
                     pdf_table_row.cell(unit)
                     pdf_table_row.cell(phone)

                     route_guest_count += 1
                     # if current_row < 38:
                     #    print(f'{current_row} ', end='')
                     current_row += 1
                     if guest_list_list[g_l_index][current_row][3][:2] != current_route[:2]:
                        #leave loop if the route changes
                        # print(f'\n{current_route=} had {route_guest_count} guests - next route is {guest_list_list[g_l_index][current_row][3]}')
                        guest_list_page_number = 0
                        break
                     if current_row >= len(guest_list_list[g_l_index]):
                        # print(f"\t  End of guest list reached at {current_row=}.")
                        break
                     # the following has to be here to avoid skipping over indexes because there is an increment outside the with
               # need to adjust current_row at the end of a table NOT SURE WHY
               current_row -= 1
               route_guest_count = 0
            else:
               current_row += 1
               current_route = "YY"

               
      except Exception as e:
         status_string = f"Failure: while making table for {pdf_report_path} exception: {e}"
         print(status_string)
         return status_string
      
   try:
      pdf.output(pdf_report_path)
   except Exception as e:
      #    current_app.logger.warning(f"PDF for {guest} failed: {e}")
      print(f"failed to generate {pdf_report_path} exception: {e}")
      return False
   return True

