# validator.py
import json
from utils.logger import log_info


def load_invoices(filename="Akaunting/data/invoices.json"):
    try:
        with open(filename, "r") as f:
            data = json.load(f)
            # Extract the nested "invoices" array from the JSON structure
            return data.get("invoices", [])
    except Exception as e:
        log_info(f"Error loading invoices: {e}")
        return []


def load_bills(filename="Akaunting/data/bills.json"):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception as e:
        log_info(f"Error loading bills: {e}")
        return []


def validate_invoice(invoice, bills):
    issues = []
    matching_bill = None
    # Search for a matching bill by vendor name, bill number, and bill date.
    for bill in bills:
        if (invoice.get("vendor_name") == bill.get("vendor_name") and
            invoice.get("bill_number") == bill.get("bill_number") and
                invoice.get("bill_date") == bill.get("bill_date")):
            matching_bill = bill
            break

    if not matching_bill:
        issues.append(
            "No matching bill found based on vendor, bill number, and bill date.")
        return issues

    # Check due date if header information matches.
    if invoice.get("due_date") != matching_bill.get("due_date"):
        issues.append(
            f"Due date mismatch: Invoice {invoice.get('due_date')} vs Bill {matching_bill.get('due_date')}")

    # Check sub_total
    if invoice.get("sub_total") != matching_bill.get("sub_total"):
        issues.append(
            f"Sub total mismatch: Invoice {invoice.get('sub_total')} vs Bill {matching_bill.get('sub_total')}")

    # Check discount details
    invoice_discount = invoice.get("discount", {})
    bill_discount = matching_bill.get("discount", {})

    if invoice_discount.get("percentage") != bill_discount.get("percentage"):
        issues.append(
            f"Discount percentage mismatch: Invoice {invoice_discount.get('percentage')} vs Bill {bill_discount.get('percentage')}")

    if invoice_discount.get("amount") != bill_discount.get("amount"):
        issues.append(
            f"Discount amount mismatch: Invoice {invoice_discount.get('amount')} vs Bill {bill_discount.get('amount')}")

    # Check tax details
    invoice_tax = invoice.get("tax", {})
    bill_tax = matching_bill.get("tax", {})

    if invoice_tax.get("tds_percent") != bill_tax.get("tds_percent"):
        issues.append(
            f"TDS percentage mismatch: Invoice {invoice_tax.get('tds_percent')} vs Bill {bill_tax.get('tds_percent')}")

    if invoice_tax.get("tds_amount") != bill_tax.get("tds_amount"):
        issues.append(
            f"TDS amount mismatch: Invoice {invoice_tax.get('tds_amount')} vs Bill {bill_tax.get('tds_amount')}")

    if invoice_tax.get("tds_tax_name") != bill_tax.get("tds_tax_name"):
        issues.append(
            f"TDS tax name mismatch: Invoice {invoice_tax.get('tds_tax_name')} vs Bill {bill_tax.get('tds_tax_name')}")

    # Check total
    if invoice.get("total") != matching_bill.get("total"):
        issues.append(
            f"Total mismatch: Invoice {invoice.get('total')} vs Bill {matching_bill.get('total')}")

    # Validate each item (item details, quantity, amount, and rate).
    invoice_items = invoice.get("items", [])
    bill_items = matching_bill.get("items", [])

    for inv_item in invoice_items:
        found_item = next((item for item in bill_items if item.get(
            "item_details") == inv_item.get("item_details")), None)
        if not found_item:
            issues.append(
                f"Item '{inv_item.get('item_details')}' not found in bill.")
            continue
        if inv_item.get("quantity") != found_item.get("quantity"):
            issues.append(
                f"Quantity mismatch for {inv_item.get('item_details')}: Invoice {inv_item.get('quantity')} vs Bill {found_item.get('quantity')}")
        if inv_item.get("amount") != found_item.get("amount"):
            issues.append(
                f"Amount mismatch for {inv_item.get('item_details')}: Invoice {inv_item.get('amount')} vs Bill {found_item.get('amount')}")
        if inv_item.get("rate") != found_item.get("rate"):
            issues.append(
                f"Rate mismatch for {inv_item.get('item_details')}: Invoice {inv_item.get('rate')} vs Bill {found_item.get('rate')}")

    return issues


def validate_all_invoices(invoices, bills):
    results = {}
    for invoice in invoices:
        inv_id = invoice.get("bill_number", "Unknown")
        issues = validate_invoice(invoice, bills)
        results[inv_id] = issues if issues else "Validated successfully."
    return results

def validate_invoice_vs_po(invoice, purchase_orders):
    """
    Validate an invoice against purchase orders (POs).
    """
    results = {
        "invoice_id": invoice.get("bill_number", "Unknown"),
        "po_validation": [],
        "overall_result": False
    }

    # Validate against purchase orders
    po_issues = validate_invoice_against_po(invoice, purchase_orders)
    results["po_validation"] = po_issues

    # Overall result is successful only if PO validation passes
    po_success = len(po_issues) == 0
    results["overall_result"] = po_success

    return results


def validate_all_invoices_vs_po(invoices, purchase_orders):
    """
    Validate all invoices against purchase orders.
    """
    results = {}
    for invoice in invoices:
        inv_id = invoice.get("bill_number", "Unknown")
        result = validate_invoice_vs_po(invoice, purchase_orders)
        results[inv_id] = result
    return results

# Add these functions to validator.py
def validate_invoice_against_po(invoice, purchase_orders):
    """
    Validate an invoice against purchase orders using bill_number → po_number match.
    """
    issues = []

    invoice_bill_number = invoice.get("bill_number", "").strip()

    # Find the matching PO by po_number
    matching_po = next((po for po in purchase_orders if po.get("po_number", "").strip() == invoice_bill_number), None)

    if not matching_po:
        issues.append(f"No matching PO found for invoice bill_number: {invoice_bill_number}")
        return issues

    # Check sub_total
    if float(invoice.get("sub_total", 0)) != float(matching_po.get("sub_total", 0)):
        issues.append(
            f"Sub total mismatch: Invoice {invoice.get('sub_total')} vs PO {matching_po.get('sub_total')}")

    # Compare items
    invoice_items = invoice.get("items", [])
    po_items = matching_po.get("items", [])

    for inv_item in invoice_items:
        found_item = next((item for item in po_items if item.get("item_details", "").strip().lower() == inv_item.get("item_details", "").strip().lower()), None)

        if not found_item:
            issues.append(f"Item '{inv_item.get('item_details')}' not found in PO.")
            continue

        # Check quantity
        if float(inv_item.get("quantity", 0)) != float(found_item.get("quantity", 0)):
            issues.append(
                f"Quantity mismatch for '{inv_item.get('item_details')}': Invoice {inv_item.get('quantity')} vs PO {found_item.get('quantity')}")

        # Check rate
        if float(inv_item.get("rate", 0)) != float(found_item.get("rate", 0)):
            issues.append(
                f"Rate mismatch for '{inv_item.get('item_details')}': Invoice {inv_item.get('rate')} vs PO {found_item.get('rate')}")

    return issues


def validate_three_way(invoice, bills, purchase_orders):
    """
    Perform a three-way validation between invoice, bill, and purchase order.
    """
    results = {
        "invoice_id": invoice.get("bill_number", "Unknown"),
        "bill_validation": [],
        "po_validation": [],
        "overall_result": False
    }

    # Validate against bills
    bill_issues = validate_invoice(invoice, bills)
    results["bill_validation"] = bill_issues

    # Validate against purchase orders
    po_issues = validate_invoice_against_po(invoice, purchase_orders)
    results["po_validation"] = po_issues

    # Overall result is successful only if both validations pass
    bill_success = len(
        bill_issues) == 0 or bill_issues == "Validated successfully."
    po_success = len(po_issues) == 0

    results["overall_result"] = bill_success and po_success

    return results


def validate_all_invoices_three_way(invoices, bills, purchase_orders):
    """
    Validate all invoices against both bills and purchase orders.
    """
    results = {}
    for invoice in invoices:
        inv_id = invoice.get("bill_number", "Unknown")
        result = validate_three_way(invoice, bills, purchase_orders)
        results[inv_id] = result
    return results

if __name__ == "__main__":
    invoices = load_invoices()
    bills = load_bills()
    results = validate_all_invoices(invoices, bills)
    for inv, result in results.items():
        print(f"Invoice {inv}:")
        if isinstance(result, list):
            for issue in result:
                print(f"  - {issue}")
        else:
            print(f"  {result}")
