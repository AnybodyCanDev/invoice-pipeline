# api.py
import requests
import json
import config
from token_manager import get_auth_headers


def get_all_bills():
    """
    Fetch all bills from Zoho Books API using the token manager for authentication.
    """
    endpoint = f"{config.ZOHO_API_DOMAIN}/books/v3/bills?organization_id={config.ZOHO_ORG_ID}"
    headers = get_auth_headers()

    try:
        print(f"Requesting from: {endpoint}")
        response = requests.get(endpoint, headers=headers)
        print("HTTP Status:", response.status_code, response.reason)

        if response.status_code == 200:
            data = response.json()
            return data.get("bills", [])
        else:
            print(
                f"Error fetching bills: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception during API request: {str(e)}")
        return []


def get_bill_id_by_number(bill_number):
    """
    Fetch the bill ID for a given bill number.
    """
    bills = get_all_bills()
    for bill in bills:
        if bill.get("bill_number") == bill_number:
            return bill.get("bill_id")
    return None


def get_bills():
    """
    Fetch bills from Zoho Books API using the token manager for authentication.
    Returns the full response data rather than trying to extract a specific field.
    """
    headers = get_auth_headers()

    try:
        print(f"Requesting from: {config.BILLS_ENDPOINT}")
        response = requests.get(config.BILLS_ENDPOINT, headers=headers)
        print("HTTP Status:", response.status_code, response.reason)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the response as JSON
            data = response.json()

            # Print the response structure to help with debugging
            print("Response keys:", list(data.keys())
                  if isinstance(data, dict) else "Not a dictionary")

            # Return the full data instead of trying to extract a specific field
            if isinstance(data, dict) and "bill" in data:
                # API returns a single bill object
                return [data["bill"]]
            elif isinstance(data, dict) and "bills" in data:
                # API returns a list of bills
                return data["bills"]
            else:
                # Return the whole response if structure is different
                return [data] if data else []
        else:
            print(
                f"Error fetching bills: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        print(f"Exception during API request: {str(e)}")
        return []

def get_purchase_order_details(purchaseorder_id):
    """
    Fetch complete details of a specific purchase order including line items.
    """
    endpoint = f"{config.ZOHO_API_DOMAIN}/books/v3/purchaseorders/{purchaseorder_id}?organization_id={config.ZOHO_ORG_ID}"
    headers = get_auth_headers()

    try:
        print(f"Requesting purchase order details from: {endpoint}")
        response = requests.get(endpoint, headers=headers)
        print("HTTP Status:", response.status_code, response.reason)

        if response.status_code == 200:
            data = response.json()
            return data.get("purchaseorder", {})
        else:
            print(
                f"Error fetching purchase order details: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        print(f"Exception during API request: {str(e)}")
        return {}

# Modified function in api.py


def get_all_purchase_orders():
    """
    Fetch all purchase orders from Zoho Books API with complete details.
    """
    endpoint = f"{config.ZOHO_API_DOMAIN}/books/v3/purchaseorders?organization_id={config.ZOHO_ORG_ID}"
    headers = get_auth_headers()

    try:
        print(f"Requesting from: {endpoint}")
        response = requests.get(endpoint, headers=headers)
        print("HTTP Status:", response.status_code, response.reason)

        if response.status_code == 200:
            data = response.json()
            purchase_orders_list = data.get("purchaseorders", [])

            # Fetch detailed information for each purchase order
            detailed_purchase_orders = []
            for po in purchase_orders_list:
                po_id = po.get("purchaseorder_id")
                if po_id:
                    detailed_po = get_purchase_order_details(po_id)
                    if detailed_po:
                        detailed_purchase_orders.append(detailed_po)

            return detailed_purchase_orders
        else:
            print(
                f"Error fetching purchase orders: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception during API request: {str(e)}")
        return []


def get_purchase_order_by_number(po_number):
    """
    Fetch a specific purchase order by its number.
    """
    purchase_orders = get_all_purchase_orders()
    for po in purchase_orders:
        if po.get("purchaseorder_number") == po_number:
            return po
    return None

def get_vendor_id_by_name(vendor_name):
    """
    Fetch the vendor ID from Zoho Books using the vendor name.
    Handles case sensitivity, spaces, and pagination.
    """
    endpoint = f"{config.ZOHO_API_DOMAIN}/books/v3/vendors?organization_id={config.ZOHO_ORG_ID}&per_page=200&page=1"
    headers = get_auth_headers()

    try:
        while endpoint:
            response = requests.get(endpoint, headers=headers)
            if response.status_code == 200:
                data = response.json()
                vendors = data.get("vendors", [])

                # Normalize input vendor name (strip spaces, lowercase)
                normalized_vendor_name = vendor_name.strip().lower()

                for vendor in vendors:
                    stored_name = vendor.get("vendor_name", "").strip().lower()
                    if stored_name == normalized_vendor_name:
                        return vendor.get("vendor_id")

                # Check if there's another page of vendors
                endpoint = data.get("page_context", {}).get("next_page", None)
            else:
                print(f"Error fetching vendors: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        print(f"Exception while fetching vendor ID: {str(e)}")

    return None  # Return None if vendor is not found
import requests
import json
import config
from token_manager import get_auth_headers

def get_all_vendors():
    """
    Fetch all vendors from Zoho Books API.
    """
    endpoint = f"{config.ZOHO_API_DOMAIN}/books/v3/vendors?organization_id={config.ZOHO_ORG_ID}&per_page=200"
    headers = get_auth_headers()

    try:
        print(f"Fetching vendors from: {endpoint}")
        response = requests.get(endpoint, headers=headers)
        print("HTTP Status:", response.status_code, response.reason)

        if response.status_code == 200:
            data = response.json()
            print("API Response:", json.dumps(data, indent=2))  # Debugging log

            # Extract vendor names from 'contacts' instead of 'vendors'
            vendors = [vendor.get("vendor_name") for vendor in data.get("contacts", [])]
            print("Vendors found in Zoho:", vendors)  # Log vendor names
            print("Raw API Response:", response.json())  # Print full response to check structure


            return vendors
        else:
            print(f"Error fetching vendors: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception during API request: {str(e)}")
        return []




