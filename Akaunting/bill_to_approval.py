import requests

import config
import os
import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add parent directory to sys.path
sys.path.append(parent_dir)

# Now import db_access
from db_access import InventoryValidator
from Akaunting.utils.logger import log_info

# Zoho API credentials from config
ZOHO_ORG_ID = config.ZOHO_ORG_ID
ZOHO_ACCESS_TOKEN = config.ZOHO_ACCESS_TOKEN
ZOHO_REFRESH_TOKEN = config.ZOHO_REFRESH_TOKEN
ZOHO_CLIENT_ID = config.ZOHO_CLIENT_ID
ZOHO_CLIENT_SECRET = config.ZOHO_CLIENT_SECRET

def get_auth_headers():
    """Generate authorization headers with a valid Zoho access token."""
    headers = {
        "Authorization": f"Zoho-oauthtoken {config.ZOHO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test if the token is valid
    test_url = f"https://www.zohoapis.in/books/v3/organizations/{config.ZOHO_ORG_ID}"
    response = requests.get(test_url, headers=headers)
    
    if response.status_code == 401:  # Unauthorized → Token expired
        log_info("🔄 Access token expired. Refreshing token...")
        new_token = refresh_access_token()
        if new_token:
            headers["Authorization"] = f"Zoho-oauthtoken {new_token}"
        else:
            log_info("❌ Could not refresh access token. Exiting.")
            return None
    
    return headers

def refresh_access_token():
    """Refresh Zoho API Access Token using the Refresh Token."""
    log_info("🔄 Access token expired. Refreshing token...")
    
    url = "https://accounts.zoho.in/oauth/v2/token"
    data = {
        "refresh_token": config.ZOHO_REFRESH_TOKEN,
        "client_id": config.ZOHO_CLIENT_ID,
        "client_secret": config.ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    
    response = requests.post(url, data=data)
    token_data = response.json()
    
    if "access_token" in token_data:
        new_token = token_data["access_token"]
        log_info("✅ Access token refreshed successfully.")
        config.ZOHO_ACCESS_TOKEN = new_token
        return new_token
    else:
        log_info(f"❌ Failed to refresh token: {token_data.get('error')}")
        return None

def submit_bill_for_approval(bill_id,po_short):
    """
    Submits a draft bill for approval in Zoho Books.
    """
    headers = get_auth_headers()
    if not headers:
        return False
    
    submit_url = f"https://www.zohoapis.in/books/v3/bills/{bill_id}/submit?organization_id={config.ZOHO_ORG_ID}"
    response = requests.post(submit_url, headers=headers)
    
    response_json = response.json()
    
    if response_json.get("code") == 0:
        validator = InventoryValidator()
        validator.test_connection()
        validator.log_to_system('invoice',po_short,{},'Converted to pending approval')
        log_info(f"✅ Bill {bill_id} is now 'Pending Approval'.")
        return True
    else:
        log_info(f"❌ Failed to submit Bill {bill_id}. Response: {response.text}")
        return False

# Example usage
if __name__ == "__main__":
    bill_id = "2353408000000090006"  # Replace with actual bill ID
    submit_bill_for_approval(bill_id)
