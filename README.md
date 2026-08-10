# Overview
The program does the following:
1. generate the list of clients (guests), where each client has some data (delivery_route, phone, address, etc)
    - it uses the [PantrySoft REST API](https://app.pantrysoft.com/api/doc) to get all the clients.
    - the client API limits each GET request to 100 entries, so it has to do a loop to get all the entries
    - a function parses the returned list of client data to extract the client information
2. generate a list of visits during the current week (Friday, Saturday).
    - If the script is not run on a Thursday, then it runs in 'test-mode' and uses hardcoded dates.
3. generate 4 bag tag PDFs for the visits (delivery, Friday, Saturday) as well as a report PDF listing the guests in alphabetical order.
4. generate 2 expeditor PDFs: pickup and delivery
5. generate 2 CSV files to be used for tracking bag counts per item count
6. upload the generated files to Google Drive: /Newbury Food Pantry/PANTRYSOFT ORDER DOCUMENTS/20xx/Tags where 20xx is the year, starting with 2026
7. Print the letter sized PDFs on the Pantry printer.

# Details

## Handling registrations
There are [registration questions](https://app.pantrysoft.com/registrationquestion/) that effect the expeditor reports.  Specifically there is the required 'registration_cell' which can be Yes or No, and the optional 'Is Priority' which can True or False.

Registrations are not required for clients - it was found that 5 clients did not have registrations.

A client can be registered multiple times; the PantrySoft API allows getting a list of registrations sorted by decreasing datetime for a client.  The API also allows getting all the registrations sorted by client or by datetime.  Since there are more than 6000 registrations, doing a query to determine the state of cell phone and priority would take time. Similarly, doing a get for every client would require more than 800 GETs - this was measured at a little under 6 mimutes.

In order to avoid extensive queries, the program will use a file, 'clients_with_priority.json' to save the lastest registration state.
A function will be written to check registrations done in the last 2 weeks to checked for Priority and Cell in order to add or drop clients in clients_with_priority.json

Tracking clients_with_landlines will be in a future release.  IMO, manual entry of cell vs landline is guarenteed to have issues - of the 72 'landline' clients, 4 of them were actually cell phones.  Using the area code may be a better indicator of cell vs landline - all of the 68 landlines had 978 as an area code.  The client's with cell numbers need to be check if any of them are 978.

# Notes:
- https://app.pantrysoft.com/api/v1/client/?limit=N returns 'count' after 'data', where the count equal to the number of active clients.
- Similarly https://app.pantrysoft.com/api/v1/registration/?client_id=N returns 'count' after 'data', with the count equal to the number of registrations.