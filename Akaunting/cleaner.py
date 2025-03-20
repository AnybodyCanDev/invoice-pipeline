# cleaner.py
import json
import datetime
# from Akaunting.logger import log_info
# utils/logger.py
import logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


def log_info(message):
    logging.info(message)


def log_error(message):
    logging.error(message)


def convert_date_format(date_str):
    """Convert date from YYYY-MM-DD to DD/MM/YYYY format."""
    if not date_str:
        return ""
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%d/%m/%Y")
    except ValueError:
        return date_str


def convert_bill_to_invoice_format(bill):
    """Convert a single bill from Zoho format to invoices.json format."""
    items = []
    for line_item in bill.get("line_items", []):
        item = {
            "item_details": line_item.get("description", ""),
            "account": line_item.get("account_name", ""),
            "quantity": line_item.get("quantity", 0),
            "rate": line_item.get("rate", 0),
            "amount": line_item.get("item_total", 0)
        }
        items.append(item)

    # Extract discount data
    discount = {
        "percentage": bill.get("discount_percent", 0),
        "amount": bill.get("discount_amount", 0)
    }

    # Extract tax data
    tax = {
        "tds_percent": bill.get("tds_percent", "0.00"),
        "tds_amount": bill.get("tds_amount", 0),
        "tds_tax_name": bill.get("tds_tax_name", "")
    }

    # Create invoice object with the same structure as in invoices.json
    invoice = {
        "vendor_name": bill.get("vendor_name", ""),
        "bill_number": bill.get("bill_number", ""),
        "bill_date": convert_date_format(bill.get("date", "")),
        "due_date": convert_date_format(bill.get("due_date", "")),
        "items": items,
        "sub_total": bill.get("sub_total", 0),
        "discount": discount,
        "tax": tax,
        "total": bill.get("total", 0)
    }
    return invoice


def clean_bills(bills):
    """Convert bills from Zoho format to match invoices.json structure."""
    cleaned_invoices = []
    for bill in bills:
        cleaned_invoice = convert_bill_to_invoice_format(bill)
        cleaned_invoices.append(cleaned_invoice)

    # Return in the same structure as invoices.json
    return {"invoices": cleaned_invoices}


def save_cleaned_bills(bills, output_file="data/cleaned_bills.json"):
    """Clean bills data and save to a file in invoices.json format."""
    cleaned_data = clean_bills(bills)

    with open(output_file, "w") as f:
        json.dump(cleaned_data, f, indent=2)

    log_info(f"Cleaned bills saved to {output_file}")
    return cleaned_data

# Add these functions to cleaner.py


def convert_po_to_invoice_format(purchase_order):
    """Convert a single purchase order from Zoho format to invoices.json format."""
    items = []
    for line_item in purchase_order.get("line_items", []):
        item = {
            "item_details": line_item.get("description", ""),
            "account": line_item.get("account_name", ""),
            "quantity": line_item.get("quantity", 0),
            "rate": line_item.get("rate", 0),
            "amount": line_item.get("item_total", 0)
        }
        items.append(item)

    # Extract discount data
    discount = {
        "percentage": purchase_order.get("discount_percent", 0),
        "amount": purchase_order.get("discount_amount", 0)
    }

    # Extract tax data - PO might have different tax structure
    tax = {
        "tds_percent": purchase_order.get("tds_percent", "0.00"),
        "tds_amount": purchase_order.get("tds_amount", 0),
        "tds_tax_name": purchase_order.get("tds_tax_name", "")
    }

    # Create invoice object with the same structure as in invoices.json
    invoice_format = {
        "vendor_name": purchase_order.get("vendor_name", ""),
        # Use PO number as reference
        "bill_number": purchase_order.get("purchaseorder_number", ""),
        # Add reference to PO number
        "po_number": purchase_order.get("purchaseorder_number", ""),
        "bill_date": convert_date_format(purchase_order.get("date", "")),
        # Might be different in PO
        "due_date": convert_date_format(purchase_order.get("delivery_date", "")),
        "items": items,
        "sub_total": purchase_order.get("sub_total", 0),
        "discount": discount,
        "tax": tax,
        "total": purchase_order.get("total", 0)
    }
    return invoice_format


def clean_purchase_orders(purchase_orders):
    """Convert purchase orders from Zoho format to match invoices.json structure."""
    cleaned_pos = []
    for po in purchase_orders:
        cleaned_po = convert_po_to_invoice_format(po)
        cleaned_pos.append(cleaned_po)

    # Return in the same structure as invoices.json
    return {"invoices": cleaned_pos}


def save_cleaned_purchase_orders(purchase_orders, output_file="data/cleaned_purchase_orders.json"):
    """Clean purchase order data and save to a file in invoices.json format."""
    cleaned_data = clean_purchase_orders(purchase_orders)

    with open(output_file, "w") as f:
        json.dump(cleaned_data, f, indent=2)

    log_info(f"Cleaned purchase orders saved to {output_file}")
    return cleaned_data

if __name__ == "__main__":
    # For testing: Load bills.json and convert it
    try:
        with open("data/bills.json", "r") as f:
            bills = json.load(f)

        cleaned_data = save_cleaned_bills(bills)
        print(
            f"Successfully converted {len(cleaned_data['invoices'])} bills to invoice format")
    except Exception as e:
        print(f"Error cleaning bills: {e}")
