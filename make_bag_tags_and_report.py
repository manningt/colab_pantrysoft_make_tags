import os
from fpdf import FPDF

from defines import DELIVERY_TYPE, AM_PM_TYPE

def item_count_to_label_count(item_count):
   limits = [0, 9, 17, 25, 32, 40, 49,57,67,73,82,90,100,107,112,139,200]
   if item_count > 200:
      return 16
   for i in range(len(limits)-1):
      if item_count > limits[i] and item_count <= limits[i+1]:
         # adjust small bag counts for July 30:
         if i < 4:
            return i + 2
         else:
            return i + 1


def make_label_pdfs(guest_list, type, pdf_filename, output_directory="."):

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
         for row in guest_list:
            label_count = int(item_count_to_label_count(row[3]))
            # print(f"  {row[0]} {row[1]} {row[2]} has {row[3]} items, which is {label_count} labels.")
            for i in range(label_count):
               pdf.add_page()
               # if row[2] is a time, then don't print it; only print if it's a route
               if type == DELIVERY_TYPE:
                  pdf.set_font_size(route_font_size)
                  pdf.cell(cell_width, cell_height, f'{row[2].replace(" - ", ": ")}', align="L")
                  pdf.line(0, 36, label_width, 36) # line from left to right
               pdf.ln(route_font_size+10)
               pdf.set_font_size(name_font_size)
               pdf.cell(cell_width, cell_height, f"{row[0].title()}", align="C")
               pdf.ln(name_font_size+4)
               pdf.cell(cell_width, cell_height, f"{row[1][0:15].title()}", align="C")
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

def write_report_file(guest_list, report_filename, output_directory="."):
   text_report_filename = report_filename.replace('.pdf', '.txt')
   text_report_path = os.path.join(output_directory, report_filename.replace('.pdf', '.txt'))
   try:
      with open(text_report_path, "w") as f:
         f.write(f"\n{text_report_filename}\n")
         # f.write(f"  First       Last     Time/Route     Items\n")
         for guest in guest_list:
            f.write(f"{guest[0]:<12} {guest[1]:<12}   {guest[2]:<20}   Items={guest[3]}\n")
   except Exception as e:
      print(f"Failed to write report file {report_filename}: {e}")  

def write_report_pdf_file(guest_list_list,  status_list, output_directory="."):
   if len(guest_list_list) == 0:
      print("Failure: no guest lists in request to generate PDF report on tag files.")
      return False
   
   pdf_report_filename = 'list-of-guests-in-tag-pdf-files.pdf'
   pdf_report_path = os.path.join(output_directory, pdf_report_filename)
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
      # print(f"\t{g_index=} {status_list[g_index]} has {len(guest_list_list[g_index])} guests.")
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
                  # first column
                  row.cell(guest_list_list[g_l_index][current_row][0][:8])
                  row.cell(guest_list_list[g_l_index][current_row][1][:14])
                  temp_text = f'{guest_list_list[g_l_index][current_row][2].replace(" - ", ": ")}'
                  row.cell(temp_text[:7])
                  row.cell(str(guest_list_list[g_l_index][current_row][3])[:3])
                  row.cell("", border=0)
                  # second column
                  index = current_row + number_of_rows_on_a_page
                  if index < len(guest_list_list[g_l_index]):
                     row.cell(guest_list_list[g_l_index][index][0][:8])
                     row.cell(guest_list_list[g_l_index][index][1][:14])
                     temp_text = f'{guest_list_list[g_l_index][index][2].replace(" - ", ": ")}'
                     row.cell(temp_text[:7])
                     row.cell(str(guest_list_list[g_l_index][index][3])[:3])
                     # print(f"\t\t{i=} {current_row=} {guest_list_list[g_index][current_row][1][:16]=} {guest_list_list[g_index][index][1][:16]=}")
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
