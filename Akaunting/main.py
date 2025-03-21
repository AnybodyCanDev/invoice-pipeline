# Update main.py with colorama for better console output
import json
import sys
import importlib
from api import get_bills, get_bill_id_by_number, get_all_purchase_orders
from validator import load_invoices, validate_all_invoices_three_way, validate_all_invoices_vs_po
from utils.logger import log_info
from cleaner import save_cleaned_bills, save_cleaned_purchase_orders
from utils.config_updater import update_bill_id_in_config
from convert_po_to_bill import convert_po_to_bill
import config
from OCR_PDF import ocr_pdf, format_with_gemini
from token_manager import get_auth_headers
import sys
import os
import subprocess
from bill_to_approval import submit_bill_for_approval
# Get the parent directory of the current script
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add parent directory to sys.path
sys.path.append(parent_dir)

# Now import db_access
from db_access import InventoryValidator
try:
    from colorama import init, Fore, Style
    colorama_available = True
    init()
except ImportError:
    colorama_available = False
    log_info("Colorama not available. Install with: pip install colorama")

import subprocess
import os

def run_ocr_extraction(pdf_file,email_id):
    """Run OCR_PDF.py with the provided PDF file path."""
    print(f"🔍 Running OCR extraction on: {pdf_file}")
    try:
        subprocess.run(["python", "Akaunting/OCR_PDF.py", pdf_file,email_id], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ OCR extraction failed: {e}")
        sys.exit(1)


import time
import requests

def get_purchase_order_id(po_number):
    """
    Fetch the purchase order ID for a given PO number from Zoho Books API.
    """
    endpoint = f"{config.ZOHO_API_DOMAIN}/books/v3/purchaseorders?organization_id={config.ZOHO_ORG_ID}"
    headers = get_auth_headers()

    try:
        print(f"🔍 Searching PO ID for PO Number: {po_number}")
        response = requests.get(endpoint, headers=headers)

        # Wait 2 seconds to ensure Zoho processes the request
        time.sleep(2)

        if response.status_code == 200:
            data = response.json()
            purchase_orders_list = data.get("purchaseorders", [])

            # Search for the PO with the matching po_number
            for po in purchase_orders_list:
                if po.get("purchaseorder_number") == po_number:
                    po_id = po.get("purchaseorder_id")
                    print(f"✅ Found PO ID: {po_id} for PO Number: {po_number}")
                    return po_id

            print(f"⚠️ No matching PO found for PO Number: {po_number}")
            return None
        else:
            print(f"❌ Error fetching PO: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None


def display_validation_results(results, po_number):
    """Display validation results with nice formatting."""
    po_short = po_number[3:]
    for invoice_id, result in results.items():
        header = f"====== Invoice {invoice_id} Validation Results ======"
        if colorama_available:
            print(f"\n{Fore.CYAN}{header}{Style.RESET_ALL}")
        else:
            print(f"\n{header}")


        # Purchase order validation results
        po_header = "Purchase Order Validation:"
        if colorama_available:
            print(f"\n{Fore.YELLOW}{po_header}{Style.RESET_ALL}")
        else:
            print(f"\n{po_header}")

        po_validation = result["po_validation"]
        if not po_validation:
            if colorama_available:
                print(
                    f"  {Fore.GREEN}✓ Invoice matches purchase order{Style.RESET_ALL}")
                validator = InventoryValidator()
                validator.test_connection()
                receipt_status = validator.update_or_insert_invoice_status(po_number)
                validator.log_to_system('invoice',po_short,{},'Invoice matched with PO')
                if receipt_status:
                    bill_id = validator.get_bill_id(po_number)
                    submit_bill_for_approval(bill_id,po_short)
                    
                    
            else:
                print(f"  ✓ Invoice matches purchase order")
        else:
            if colorama_available:
                print(
                    f"  {Fore.RED}✗ Issues found with purchase order:{Style.RESET_ALL}")
                validator.log_to_system('invoice',po_short,issue,'Invoice not matched with PO')
            else:
                print(f"  ✗ Issues found with purchase order:")
            for issue in po_validation:
                print(f"    - {issue}")

        if colorama_available:
            print(f"\n{Fore.CYAN}{'='*45}{Style.RESET_ALL}\n")
        else:
            print(f"\n{'='*45}\n")


def main():
    # Load invoices from local file.
    # run_ocr_extraction()
    # print(get_purchase_order_id("try_draft"))
    if len(sys.argv) < 3:
        print("❌ No PDF file provided. Exiting.")
        sys.exit(1)

    pdf_file = sys.argv[1]  # Get file path from Kafka consumer
    email_id = sys.argv[2] # Get email ID from Kafka consumer
    run_ocr_extraction(pdf_file, email_id)
    print(f"✅ Running OCR on: {pdf_file}")
    pdf_name = os.path.splitext(os.path.basename(pdf_file))[0]

    invoices = load_invoices()
    if not invoices:
        log_info("No invoices found in data/invoices.json")
        return

    # Fetch purchase orders
    log_info("Fetching purchase orders from Zoho Books API...")
    purchase_orders = get_all_purchase_orders()
    if not purchase_orders:
        log_info("No purchase orders fetched from Zoho API.")
        return

    # Save the raw fetched purchase orders to a local file.
    with open("Akaunting/data/purchase_orders.json", "w") as f:
        json.dump(purchase_orders, f, indent=4)
    log_info("Raw purchase orders saved to data/purchase_orders.json")

    # Clean and convert purchase orders to match invoices.json format
    log_info("Cleaning purchase orders data to match invoice format...")
    cleaned_pos_data = save_cleaned_purchase_orders(
        purchase_orders, "Akaunting/data/cleaned_purchase_orders.json")
    cleaned_pos = cleaned_pos_data["invoices"]

    # Validate invoices against the cleaned bills and purchase orders
    log_info("Performing validation between PO and Invoice...")
    results = validate_all_invoices_vs_po(
        invoices, cleaned_pos)
    
    # Convert matched POs to Bills
    for invoice_id, result in results.items():
        if result["overall_result"]:  # If PO validation passed
            po_number = invoice_id  # Assuming invoice_id is same as po_number
            po_short = po_number[3:]
            po_id = get_purchase_order_id(po_number)  # Fetch only required PO ID            if po_id:
            log_info(f"🔄 Converting matched PO {po_id} to Bill...")
            convert_po_to_bill(po_short,po_id, email_id)
        else:
            log_info("⚠️ No matching PO found to convert.")

    # Display results with nice formatting
    display_validation_results(results,po_number)


if __name__ == "__main__":
    main()
