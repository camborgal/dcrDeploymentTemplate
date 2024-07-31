import requests
from bs4 import BeautifulSoup
import json
import sys
import os
from copy import deepcopy

# Base URL to MSFT Docs
base_url = "https://learn.microsoft.com/"
# Specific path for tables supported with the Log Ingestion API
supportedTablesPath = "/en-us/azure/azure-monitor/logs/logs-ingestion-api-overview#supported-tables"
# Used to filter links returned when scraping the MSFT page
tablesPath = "/en-us/azure/azure-monitor/reference/tables/"
# used to grab the Cribl DCR Deployment Template from Cribl docs
dcrTemplateURL = "https://docs.cribl.io/stream/usecase-webhook-azure-sentinel-dcr-template/"

# Initiate the supported and selected table arrays
supportedTables = []
selectedTables = []
dcrTemplate = {}

# Return list of Azure Monitor Tables that support API Ingestion
def get_supported_tables(url, filter):
    # Scrape the Tables that support API Ingestion
    response = requests.get(url)
   
    if response.status_code == 200:
        # Parse the HTML, and look for all link tags with href
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)
    
        # Create empty table array 
        supportedTables = []

        # For each link tag found, grab the href value,
        # Ensure it is a link to a table using the regex 
        # Append the table name to the table array
        for link in links:
            href = link.get('href')

            if href and href.startswith(filter):
                supportedTables.append(link.text)

        return supportedTables
    
    else:
        return None

# Return required fields and data types for requested Azure Monitor Table
def parseTableDetails(base_url,path,table):
    # Scrape HTML from the specific Table schema documentation
    response = requests.get(base_url + path + table)

    if response.status_code == 200:
        table_dict = []
        # Parse the HTML request, grab the last table on the page 
        # This should be the required fields and types
        # Then, grab the rows within the table
        try:
            rows = BeautifulSoup(response.content, 'html.parser').find_all('table')[-1].find_all('tr')
            # Iterate through all the rows skipping the first row (header)
            # Skip any field names that start with '_' (internal Sentinel fields)
            # Grab the first two td elements within the row, create a dict, and append that dict to table_dict array
            for row in rows[1:]:
                if not(row.text.strip().startswith('_') or row.text.strip().startswith('TenantId')):
                    cells = row.find_all('td')[:-1]
                    dict_entry = {'name': cells[0].text, 'type': cells[1].text}
                    table_dict.append(dict_entry)
            
            return table_dict
        except IndexError:
            return None
    
    else:
        return None

# Load the DCR Deployment Template from Cribl docs
def loadDCRTemplate(url):
    response = requests.get(url)

    if response.status_code == 200:
        # Parse the HTML, and look for all link tags with 'code'
        html = BeautifulSoup(response.content, 'html.parser').find_all('code')
        template = ""

        # Iterate through all the code tags to create the template
        for item in html:
            template = template + (item.text)

        # Convert to dictionary to remove the template streamDeclarations and dataFlows
        template = json.loads(template)
        template["resources"][0]["properties"]["streamDeclarations"].clear()
        template["resources"][0]["properties"]["dataFlows"].clear()

        # Return the blank template as a string
        return template

# Return dataFlow object. This goes into the DCR 
def dataFlow(tableName):

    # Create the dataFlow object based on the table_name
    entry = {"streams": ["Custom-" + tableName], "destinations": ["logAnalyticsWorkspace"],"transformKql": "source","outputStream": "Microsoft-" + tableName}

    return entry



# Take the DCR Template and build based on passed table
#def build_dcr(dcr_template,tableColumns):
    
    # Start the DCR with the template
    dcr = dcr_template

    # Gather list of Ingestion API compatible tables
    supportedTables = get_supported_tables(base_url + supportedTablesPath, tablesPath)

    

    # Add in the streamDeclarations for the Table (columns and datatypes)
    dcr["resources"][0]["properties"]["streamDeclarations"]["Custom-" + "Syslog"] = {"columns": tableColumns}

    # Add in the dataFlow object
    dcr["resources"][0]["properties"]["dataFlows"].append(dataFlow("Syslog"))
    
    return json.dumps(dcr)

# Build the DCR Deployment Template
def buildDCR(tablesForDCR):

    # Start the DCR with the template
    dcr = deepcopy(dcrTemplate)

    # Create temporary lowercase copy of supportedTables for case-insensitve check
    lowerSupportedTables = [item.lower() for item in supportedTables]

    # Iterate through provided list of tables
    for table in tablesForDCR:
        # Case-insentive check desired table exists in supported tables.
        # Use index to grab the correct table name with correct capitalization from the supported tables list
        for index, item in enumerate(lowerSupportedTables):
            # Check that the desired table is not a duplicate 
            if (item.lower() == table.lower() and ('Custom-' + supportedTables[index] not in dcr["resources"][0]["properties"]["streamDeclarations"])):
                # Add in the streamDeclarations for the Table (columns and datatypes)
                dcr["resources"][0]["properties"]["streamDeclarations"]["Custom-" + supportedTables[index]] = {"columns": parseTableDetails(base_url,tablesPath,supportedTables[index])}
                # Add in the dataFlow object
                dcr["resources"][0]["properties"]["dataFlows"].append(dataFlow(supportedTables[index]))
                break          

    return json.dumps(dcr)

# Add supported Table to DCR Template
def addTable():
    
    # Print all the supported tables
    print('\nSelect a supported table to add to the DCR Deployment Template:')
    for index, table in enumerate(supportedTables):
        print(f"{index+1}. {table}")

    # Wait for numeric selection
    while True:
        try:
            userInput = int(input(("Choose a table (number) to add, or select 0 to return to menu: ")))
            
            # If the selection is valid, grab the selected table, and return it
            if 1 <= userInput <= len(supportedTables):
                if supportedTables[userInput-1] not in selectedTables:
                    print('\nTable ' + str(userInput) + ". " + supportedTables[userInput-1] + " added\n")
                    selectedTables.append(supportedTables[userInput-1])
                    return
                else:
                    print("Selection already chosen\n")
            elif userInput == 0:
                print('Returning to main menu\n')
                return
            else:
                print("Invalid choice. Enter a number between 1 and ", len(supportedTables))
                print('')
        
        except ValueError:
            print("Invalid input. Enter a number.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit()

# Remove a table from previously selected tables
def removeTable():
    
    # Print the enumerated contents of 'selectedTables' 
    print('\nSelect a table to remove from the DCR Deployment Template:\n')
    for index, table in enumerate(selectedTables):
        print(f"{index+1}. {table}")

    while True:
        try:
            # Wait for a numeric input for table to remove. Includes basic validation
            # Once a valid choice has been made, pop that entry and return to main userInput loop
            userInput = int(input(("\nChoose a table (number) to remove: ")))
            if 1 <= userInput <= len(selectedTables):
                removedTable = str(selectedTables.pop(userInput-1))
                print('Table ' + str(userInput) + ". " + removedTable + " removed\n")
                return
            else:
                print("Invalid choice. Enter a number between 1 and ", len(selectedTables))
        
        except ValueError:
            print("Invalid input. Enter a number.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit()

# Print selectedTable
def printTable():
    print('\nThe following tables have been added to the DCR Deployment:')
    # Iterate through enumerated selectedTables and print
    for index, table in enumerate(selectedTables):
        print(f"{index+1}. {table}")
    print('')

# Gather input
def userInput():
    
    print("Welcome to the DCR Deployment Template Builder")

    while True:
        try:
            print("Choose from the following options:")
            print("A: Add a table to the DCR Deployment Template")
            print("B: Remove a selected table")
            print("C: Print the table(s) already selected")
            print("D: Create the DCR Deployment Template")
            print("E: Create an individual template for each supported table")
            print("F: Exit and quit")
            userInput = str(input("Choose an option (A-F): ")).lower()
            
            # Print the supported tables and await numeric selection
            # Add selected table to the selectedTable array
            if userInput == 'a':
                if len(selectedTables) < 11:
                    addTable()
                else:
                    print('Max (10) amount of tables selected')

            # Selection to remove a table from the selected Tables
            # Print the selectedTables and await input
            elif userInput == 'b':
                if selectedTables:
                    removeTable()
                else:
                    print('\nNo tables have been added\n')

            # Print the selectedTables array
            elif userInput == 'c':
                if selectedTables:
                    printTable()
                else:
                    print('\nNo tables have been added\n')

            # Return selectedTables for DCR buildout, unless empty
            elif userInput == 'd':
                if selectedTables:
                    writeDCR(buildDCR(selectedTables),selectedTables)
                    print('\nDCR Deployment template created\n')
                else:
                    print("No tables selected!\n")
            
            elif userInput == 'e':
                for table in supportedTables:
                    writeDCR(buildDCR([table]),[table])
                    #writeDCR(buildDCR(table))
                print('\nDCR Deployment Template created for each supported table\n')
                return

            # Quit the program
            elif userInput == 'f':
                print('\nExiting...')
                sys.exit()
            
            # Bad selection
            else:
                print("Invalid choice. Choose an option (A-F)\n")

        except ValueError:
            print("Invalid input. Enter a number.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit()

# Write DCR Deployment Templates to file
def writeDCR(dcr,tableArray):
   
    path = 'templates/'
    os.makedirs(path, exist_ok=True)

    if len(tableArray) > 1:
        filename = 'dcr-Combined-' + str(len(tableArray)) + '.json'
    else:
        filename = 'dcr-' + tableArray[0] + '-' + str(len(tableArray)) + '.json'
    
    with open(path + filename, 'w') as f:
        f.write(dcr)

if __name__ == '__main__':

    supportedTables = get_supported_tables(base_url + supportedTablesPath, tablesPath)
    dcrTemplate = loadDCRTemplate(dcrTemplateURL)

    userInput()

    