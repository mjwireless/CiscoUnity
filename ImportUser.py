import os
import requests
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import json
import logging

# Initialize logging
logging.basicConfig(filename='script.log', level=logging.INFO, format='%(asctime)s - %(message)s')  # Add timestamp

# Load User to query
sAMAccountName = "NetoworkName"  # Define the samaccountname variable
template_alias = "template name"  # Replace with the desired template alias
dtmf_access_id = "5551212"  # Replace with the desired dtmfAccessId

payload = {
    "dtmfAccessId": dtmf_access_id,
    "pkid": ""  # Initialize pkid to an empty string
    # Include other necessary payload data
}

# Function to create a session with retries
def create_session(retries, backoff_factor, status_forcelist):
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        status_forcelist=status_forcelist,
        backoff_factor=backoff_factor,
        allowed_methods=frozenset(['GET', 'POST'])
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Configure retries for 503 errors with a delay
retries = 3  # Number of retries
backoff_factor = 2  # Delay factor (exponential backoff)
status_forcelist = [503]  # Retry on 503 errors

# Create a session with retries
session = create_session(retries, backoff_factor, status_forcelist)
logging.info("Session Start")  # Changed error to info

# Load configuration from a JSON file
config_file = 'config.json'
if os.path.exists(config_file):
    with open(config_file, 'r') as file:
        config = json.load(file)
        username = config.get('username')
        password = config.get('password')
        base_url = config.get('base_url')
    if not (username and password and base_url):
        logging.error("Invalid or incomplete configuration in config.json")
        exit(1)
else:
    logging.error("Config file 'config.json' not found.")
    exit(1)

# Summarize User pass
authentication = (username, password)

# Function for logging and reporting errors
def report_error(message, error):
    logging.error(message)
    if error:
        logging.exception(error)
    print(f"Error: {message}")

# Define the URLs
get_import_url = f"{base_url}vmrest/import/users/ldap?query=(alias%20is%20{sAMAccountName})"
current_user_url = f"{base_url}vmrest/users?query=(alias%20is%20{sAMAccountName})"
number_exists_url = f"{base_url}vmrest/users?query=(DtmfAccessId is {dtmf_access_id})"
template_exists_url = f"{base_url}vmrest/usertemplates?query=(Alias%20is%20{template_alias})"
post_import_url = f"{base_url}vmrest/import/users/ldap?templateAlias={template_alias}"
####################################
# First Let's Make sure the number does not already Exist
current_number_found = False
for retry in range(retries + 1):
    number_exists = session.get(number_exists_url, auth=authentication)
    if number_exists.status_code == 503:
        logging.info(f"Received 503 error. Retrying attempt {retry + 1}/{retries + 1}...")
        time.sleep(backoff_factor * (2 ** retry))  
    elif number_exists.status_code == 200:
        logging.info("Get current_number Connection is 200 OK")
        number_exists_root = ET.fromstring(number_exists.text)
        number_exists_total = int(number_exists_root.get('total'))
        if number_exists_total == 0:  
            logging.info("Current Number Not In Use")
            logging.info(number_exists.text)
            break  
        elif number_exists_total == 1:  
            user_element = number_exists_root.find('User')
            if user_element is not None:
                number_alias = user_element.find('Alias').text
                number_first_name = user_element.find('FirstName').text
                number_last_name = user_element.find('LastName').text
                number_pkid = user_element.find('ObjectId').text
                logging.error("Existing Number found:")
                logging.info(f"Alias: {number_alias}")
                logging.info(f"First Name: {number_first_name}")
                logging.info(f"Last Name: {number_last_name}")
                logging.info(f"PKID: {number_pkid}")
                logging.info(f"XML:  {number_exists.text}")
                current_number_found = True
                break  # Number found, exit the loop
        else:
            report_error(f"Request failed with status code {number_exists.status_code}", None)
            break
if current_number_found:
    print("Number is already in use")
else:
    print("Number is Available")
    logging.error("Number is Available")
####################################
#Second Let's Query if the Template Exists
    current_template_found = False
    for retry in range(retries + 1):
        template_exists = session.get(template_exists_url, auth=authentication)
        if template_exists.status_code == 503:
            logging.info(f"Received 503 error. Retrying attempt {retry + 1}/{retries + 1}...")
            time.sleep(backoff_factor * (2 ** retry))
        elif template_exists.status_code == 200:
            logging.info("Get template_exists Connection is 200 OK")
            template_exists_root = ET.fromstring(template_exists.text)
            template_exists_total = int(template_exists_root.get('total'))
            if template_exists_total == 0:
                logging.error("template is not Valid")
                logging.info(template_exists.text)
                break 
            elif template_exists_total == 1:
                user_element = template_exists_root.find('UserTemplate')
                if user_element is not None:
                    template_exists_alias = user_element.find('Alias').text
                    template_exists_pkid = user_element.find('ObjectId').text
                    print("Template Found")
                    logging.info("Template Found:")
                    logging.info(f"Alias: {template_exists_alias}")
                    logging.info(f"PKID: {template_exists_pkid}")
                    logging.info(f"XML:  {template_exists.text}")
                    current_template_found = True
                    break  # Number found, exit the loop
            else:
                report_error(f"Request failed with status code {template_exists.status_code}", None)
                break
    if not current_template_found:
        print("Error: template is not Valid")
    else: 
####################################
    # Third Let's Query if the user Exists
        current_user_found = False
        for retry in range(retries + 1):
            is_current_user = session.get(current_user_url, auth=authentication)
            if is_current_user.status_code == 503:
                logging.info(f"Received 503 error. Retrying attempt {retry + 1}/{retries + 1}...")
                time.sleep(backoff_factor * (2 ** retry))
            elif is_current_user.status_code == 200:
                logging.info("Get current_user Connection is 200 OK")
                is_current_user_root = ET.fromstring(is_current_user.text)
                is_current_user_total = int(is_current_user_root.get('total'))
                if is_current_user_total == 0:
                    print("The user does not already Exist")
                    logging.info("Current User Not Found")
                    logging.info(is_current_user.text)
                    break
                elif is_current_user_total == 1:
                    user_element = is_current_user_root.find('User')
                    if user_element is not None:
                        current_alias = user_element.find('Alias').text
                        current_first_name = user_element.find('FirstName').text
                        current_last_name = user_element.find('LastName').text
                        current_pkid = user_element.find('ObjectId').text
                        logging.error("Existing User found:")
                        logging.info(f"Alias: {current_alias}")
                        logging.info(f"First Name: {current_first_name}")
                        logging.info(f"Last Name: {current_last_name}")
                        logging.info(f"PKID: {current_pkid}")
                        logging.info(f"XML:  {current_alias.text}")
                        current_user_found = True
                        break  # User found, exit the loop
            else:
                report_error(f"Request failed with status code {is_current_user.status_code}", None)
                break
        if current_user_found:
            print("Error: User Already Configured")
        else:  
####################################
    # Fourth Let's Query if that user is avalable for import
            import_user_found = False
            importable_user = None
            for retry in range(retries + 1):
                importable_user = session.get(get_import_url, auth=authentication)
                if importable_user.status_code == 503:
                    logging.info(f"Received 503 error. Retrying attempt {retry + 1}/{retries + 1}...")
                    time.sleep(backoff_factor * (2 ** retry))  # Exponential backoff
                elif importable_user.status_code == 200:
                    logging.info("import_url 200 OK")
                    root = ET.fromstring(importable_user.text)
                    importable_user_total = int(root.get('total'))
                    if importable_user_total == 0:
                        logging.error("Import User Not Found")
                        # If The user does not exits there is no one to import
                        break
                    if importable_user_total == 1:
                        for user_element in root.findall('.//ImportUser'):
                            importable_alias = user_element.find('alias').text
                            importable_first_name = user_element.find('firstName').text
                            importable_last_name = user_element.find('lastName').text
                            importable_pkid = user_element.find('pkid').text
                            print("Import User found:")
                            logging.info("Import User found:")
                            logging.info(f"Alias: {importable_alias}")
                            logging.info(f"First Name: {importable_first_name}")
                            logging.info(f"Last Name: {importable_last_name}")
                            logging.info(f"PKID: {importable_pkid}")
                            logging.info(f"XML:  {importable_user.text}")
                            payload["pkid"] = importable_pkid
                            import_user_found = True
                            break  # Exit the loop
            if not import_user_found:
                print("Error: Import User Not Found")
            else:
                # Perform the POST request to the import URL with the JSON payload and retries
                for retry in range(retries + 1):
                    post_import = session.post(post_import_url, json=payload, auth=authentication)
                    if post_import.status_code == 503:
                        logging.info(f"Received 503 error. Retrying attempt {retry + 1}/{retries + 1}...")
                        time.sleep(backoff_factor * (2 ** retry))  # Exponential backoff
                    elif post_import.status_code == 201:
                        print("User Created")
                        logging.info("User Created")
                        # Extract and log user details from the import response
                        for user_element in root.findall('.//ImportUser'):
                            alias = user_element.find('alias').text
                            first_name = user_element.find('firstName').text
                            last_name = user_element.find('lastName').text
                            pkid = user_element.find('pkid').text
                            logging.info("Import User found:")
                            logging.info(f"Alias: {alias}")
                            logging.info(f"First Name: {first_name}")
                            logging.info(f"Last Name: {last_name}")
                            logging.info(f"PKID: {pkid}")
                            logging.info(f"XML:  {post_import.text}") 
                        break  # Exit the loop since the user was successfully created
                    elif post_import.status_code == 200:
                        logging.info(f"Import URL 200 OK for templateAlias '{template_alias}':")
                        root = ET.fromstring(post_import.text)
                        total = int(root.get('total'))
                        if total == 0:
                            print("No users found for the templateAlias")
                            logging.info("No users found for the templateAlias")
                            break  # Exit the loop
                    elif post_import.status_code == 400:
                        logging.info(f"Bad Request (400):")
                        try:
                            error_root = ET.fromstring(post_import.text)
                            error_code = error_root.find('.//code').text
                            error_message = error_root.find('.//message').text
                            logging.info(f"Error Code: {error_code}")
                            logging.info(f"Error Message: {error_message}")
                        except Exception as e:
                            report_error("Failed to parse error post_import:", e)
                        break  # Exit the loop
                    elif post_import.status_code == 404:
                        logging.info(f"Resource Not Found (404):")
                        try:
                            error_root = ET.fromstring(post_import.text)
                            error_code = error_root.find('.//code').text
                            error_message = error_root.find('.//message').text
                            logging.info(f"Error Code: {error_code}")
                            logging.info(f"Error Message: {error_message}")
                        except Exception as e:
                            report_error("Failed to parse error post_import:", e)
                        break  # Exit the loop
                    else:
                        report_error(f"Request failed with status code {post_import.status_code}", None)
                        break  # Exit the loop since there was an unexpected error
