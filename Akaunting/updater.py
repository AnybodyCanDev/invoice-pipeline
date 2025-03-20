import psycopg2
import requests
import config  # Your Zoho API config
from datetime import datetime
from convert_po_to_bill import refresh_access_token

# Connect to PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        dbname="grn_tracking",
        user="kriti.bharadwaj03",  # Change this to your PostgreSQL username
        password="abcd_deloitte1",  # Change this to your PostgreSQL password
        host="localhost",
        port="5432"
    )

def get_bill_id_from_number(bill_number):
    """
    Searches for a bill in Zoho using the bill number and retrieves the corresponding bill ID.
    """
    url = f"https://www.zohoapis.in/books/v3/bills?organization_id={config.ZOHO_ORG_ID}&bill_number={bill_number}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {config.ZOHO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    # 🔹 Handle expired token
    if response.status_code == 401:
        print("🔄 Access token expired. Refreshing token...")
        refresh_access_token()
        headers["Authorization"] = f"Zoho-oauthtoken {config.ZOHO_ACCESS_TOKEN}"  # Update token
        response = requests.get(url, headers=headers)  # Retry

    data = response.json()
    print(data)

    if data.get("code") == 0 and data.get("bills"):
        return data["bills"][0]["bill_id"]  # Return the first matching bill ID
    else:
        print(f"❌ Error fetching Bill ID: {data.get('message')}")
        return None
    
# Function to fetch bill details from Zoho
def fetch_bill_from_zoho(bill_id):
    url = f"https://www.zohoapis.in/books/v3/bills/{bill_id}?organization_id={config.ZOHO_ORG_ID}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {config.ZOHO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 401:
        print("🔄 Access token expired. Refreshing token...")
        refresh_access_token()
        response = requests.get(url, headers=headers)

    data = response.json()
    if data.get("code") == 0:
        return data.get("bill", {}).get("line_items", [])  # Fetch bill line items
    else:
        print(f"❌ Error fetching Bill details: {data.get('message')}")
        return None

# Insert new items from a bill into the database
def insert_bill_items(po_id, line_items):
    conn = get_db_connection()
    cursor = conn.cursor()

    for item in line_items:
        item_name = item["name"] if item["name"] else item["description"]
        quantity = item["quantity"]

        # Check if the item already exists
        cursor.execute("SELECT * FROM grn_tracking WHERE po_id = %s AND item_name = %s", (po_id, item_name))
        existing_row = cursor.fetchone()

        if not existing_row:
            # Insert new item
            cursor.execute("""
                INSERT INTO grn_tracking (po_id, item_name, initial_quantity, remaining_quantity, last_received)
                VALUES (%s, %s, %s, %s, %s)
            """, (po_id, item_name, quantity, quantity, datetime.now()))
            print(f"✅ Inserted {quantity} of {item_name} for PO {po_id}")

    conn.commit()
    cursor.close()
    conn.close()

# Update received quantities
def update_received_quantity(po_id, received_items):
    conn = get_db_connection()
    cursor = conn.cursor()

    for item_name, received_qty in received_items.items():
        cursor.execute("""
            UPDATE grn_tracking
            SET remaining_quantity = remaining_quantity - %s, last_received = %s
            WHERE po_id = %s AND item_name = %s
        """, (received_qty, datetime.now(), po_id, item_name))
        print(f"🔄 Updated {item_name}: -{received_qty} for PO {po_id}")

    conn.commit()
    cursor.close()
    conn.close()

# Check if all quantities are zero and match with the bill
def check_full_receipt(po_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(remaining_quantity) FROM grn_tracking WHERE po_id = %s", (po_id,))
    remaining_qty = cursor.fetchone()[0]

    if remaining_qty == 0:
        print(f"✅ All items received for PO {po_id}. Proceeding to payment pipeline!")
        # Send it for final verification/matching with Zoho
        match_with_bill(po_id)

    cursor.close()
    conn.close()

# Match with bill in Zoho
def match_with_bill(po_id):
    print(f"🔍 Matching PO {po_id} with the bill in Zoho...")
    # Here, you can implement further verification logic if needed

# Test the script
if __name__ == "__main__":
    bill_number = "PO-00003"  # Replace with actual bill number
    bill_id = get_bill_id_from_number(bill_number)

    if bill_id:
        bill_items = fetch_bill_from_zoho(bill_id)
        print(bill_items)
    else:
        print("⚠️ No bill found for the given bill number.")
    
    # Step 1: Fetch bill details and store in DB
    line_items = bill_items
    if line_items:
        insert_bill_items(bill_number, line_items)

    # Step 2: Simulating received shipments
    received_shipment_1 = {"Lipstick": 3}  # First shipment received
    update_received_quantity(bill_number, received_shipment_1)
    check_full_receipt(bill_number)

    received_shipment_2 = {"Hat": 2, "Sunscreen": 1}  # Final shipment received
    update_received_quantity(bill_number, received_shipment_2)
    check_full_receipt(bill_number)
