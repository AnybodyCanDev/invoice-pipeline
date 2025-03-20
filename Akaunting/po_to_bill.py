import requests
import json

# Zoho API credentials
ZOHO_ORG_ID = "60038600013"
ZOHO_ACCESS_TOKEN = "1000.99a4af0492d8fa1b3fcdf1318ac7be23.3ef453375c49aaa5cbf0403f00f7e084"
HEADERS = {
    "Authorization": f"Zoho-oauthtoken {ZOHO_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Purchase Order ID to convert
PURCHASE_ORDER_ID = "2353408000000069062"

# Step 1: Fetch the Purchase Order details
def get_purchase_order():
    url = f"https://www.zohoapis.in/books/v3/purchaseorders/{PURCHASE_ORDER_ID}?organization_id={ZOHO_ORG_ID}"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    if data.get("code") == 0:
        print(f"✅ Purchase Order {PURCHASE_ORDER_ID} found.")
        return data["purchaseorder"]
    else:
        print(f"❌ Error fetching PO: {data.get('message')}")
        return None

# Step 2: Convert Purchase Order to Bill
def convert_po_to_bill():
    url = f"https://www.zohoapis.in/books/v3/bills/editpage/frompurchaseorders?purchaseorder_ids={PURCHASE_ORDER_ID}&organization_id={ZOHO_ORG_ID}"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    
    if data.get("code") == 0:
        bill_data = data["bill"]
        
        # Retaining only necessary fields
        filtered_bill_data = {
            "purchaseorder_ids": bill_data.get("purchaseorder_ids"),
            "vendor_id": bill_data.get("vendor_id"),
            "bill_number": f"BILL-{bill_data.get('reference_number', PURCHASE_ORDER_ID)}",
            "date": bill_data.get("date"),
            "due_date": bill_data.get("due_date"),
            "currency_id": bill_data.get("currency_id"),
            "line_items": bill_data.get("line_items", []),  # Ensure line items exist
            "reference_number": bill_data.get("reference_number"),
            "status": "draft"  # Set the status to open
        }
        
        return filtered_bill_data
    else:
        print(f"❌ Error converting PO to Bill: {data.get('message')}")
        return None

# Step 3: Create & Finalize the Bill
def create_bill(bill_data):
    url = f"https://www.zohoapis.in/books/v3/bills?organization_id={ZOHO_ORG_ID}"
    response = requests.post(url, headers=HEADERS, json=bill_data)
    data = response.json()
    
    if data.get("code") == 0:
        bill_id = data["bill"]["bill_id"]
        print(f"✅ Bill {bill_id} created successfully.")
        return bill_id
    else:
        print(f"❌ Error creating Bill: {data.get('message')}")
        return None

# Run the steps
purchase_order = get_purchase_order()
if purchase_order:
    bill_data = convert_po_to_bill()
    if bill_data:
        create_bill(bill_data)
