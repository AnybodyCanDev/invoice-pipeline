from db_access import InventoryValidator
import json
from Akaunting.utils.logger import log_info


def load_invoices(filename="Akaunting/data/invoices.json"):
    try:
        with open(filename, "r") as f:
            data = json.load(f)
            # Extract the nested "invoices" array from the JSON structure
            return data.get("invoices", [])
    except Exception as e:
        log_info(f"Error loading invoices: {e}")
        return []
    
def test_inventory_validator():
    validator = InventoryValidator()
    validator.test_connection()
    # invoice_data = load_invoices()
    # print(f"Loaded invoice data: {type(invoice_data)} -> {invoice_data}")  # Debugging

    # if invoice_data:  # Ensure there is data before inserting
    #     validator.insert_invoice({"invoices": invoice_data})  # Pass as dict
    # else:
    #     log_info("No invoices found to insert.")
    email_id = "195adabd9c40bae5"
    bill_id = "2353408000000085006"
    validator.update_or_insert_invoice_status("PO-00014")
    # validator.insert_bill_id(bill_id, email_id)
        
test_inventory_validator()
    