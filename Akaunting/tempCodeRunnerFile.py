# main.py
import json
from api import get_bills
from validator import load_invoices, validate_all_invoices
from Akaunting.utils.logger import log_info


def main():
    log_info("Fetching bills from Zoho Books API...")
    bills = get_bills()
    if not bills:
        log_info(
            "No bills fetched from Zoho API. Check your API credentials and endpoint.")
        return

    # Save the fetched bills to a local file.
    with open("data/bills.json", "w") as f:
        json.dump(bills, f, indent=4)
    log_info("Bills saved to data/bills.json")

    # Load invoices from local file.
    invoices = load_invoices()
    if not invoices:
        log_info("No invoices found in data/invoices.json")
        return

    # Validate invoices against the fetched bills.
    results = validate_all_invoices(invoices, bills)
    for invoice_id, result in results.items():
        log_info(f"Invoice {invoice_id}:")
        if isinstance(result, list):
            for issue in result:
                log_info(f"  - {issue}")
        else:
            log_info(f"  {result}")


if __name__ == "__main__":
    main()
