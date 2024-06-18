# dcrDeploymentTemplate
Author: Cameron Borgal
Date: 6/18/2024
Version: 0.1


Welcome to the Azure DCR Deployment Template Builder

The motivation behind the project is to enable quick DCR deployments for Cribl Stream to send data to the desired Sentinel/Log Analytic tables (that are suported by the Azure Log Ingestion API).

Things to note:
1. 'Tables' refer to the list of tables supported by the Log Ingestion API only. (https://learn.microsoft.com/en-us/azure/azure-monitor/logs/logs-ingestion-api-overview#supported-tables)
2. The script is interactive. You can add/remove tables from your selection, then build the template. You can also just create a deployment template for each supported table (take a look at templates/)
3. You can only have a max of 10 tables per template
4. This script dynamically builds the required columns and data types from MSFTs documentation. If MSFT decides to change the schema of a table or add/remove tables supported by the Log Ingestion API, simply rerun the script to build a new template.

How to use:
1. Run the python script. The following packages are used: requests, BeautifulSoup, json, sys, os, deepcopy
2. Follow the prompts.
3. DCR Deployment templates will be created in a new directory called 'templates'

Version 0.1 Release Notes
* Initial release