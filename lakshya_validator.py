# inventory_validator.py
import json
import datetime
import psycopg2
import psycopg2.extras
import requests
import traceback
from Akaunting.utils.logger import log_info, log_error
from Akaunting.token_manager import get_auth_headers
from Akaunting.bill_to_approval import submit_bill_for_approval
import config 


class InventoryValidator:
    def __init__(self):
        """Initialize the inventory validator with database configuration."""
        self.db_url = "DATABASE_URL"
        self.conn = None
        self.cursor = None
        self._connect_db()

    def _connect_db(self):
        """Establish a database connection."""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor(
                cursor_factory=psycopg2.extras.DictCursor)
            log_info("Connected to database successfully")
        except Exception as e:
            log_error(f"Error connecting to database: {str(e)}")
            traceback.print_exc()

    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if needed."""
        if not self.conn or self.conn.closed:
            self._connect_db()
        return self.conn and not self.conn.closed

    def _raise_flag(self, zoho_po_number, flag_type, flag_description, receipt_id=None):
        """
        Raise a flag for a problematic PO.
        
        Args:
            zoho_po_number (str): PO number with issue
            flag_type (str): Type of flag/issue
            flag_description (str): Detailed description
            receipt_id (int, optional): ID of receipt that triggered the flag
        """
        try:
            if not self._ensure_connection():
                log_error("Database connection failed")
                return False

            # Add receipt_id to description if provided
            full_description = flag_description
            if receipt_id:
                full_description = f"Receipt ID {receipt_id}: {flag_description}"

            log_info(
                f"Raising flag for PO {zoho_po_number}: {flag_type} (Receipt ID: {receipt_id if receipt_id else 'None'})")

            self.cursor.execute(
                """INSERT INTO "RaiseFlags" (zoho_po_number, flag_type, flag_description, created_at)
                VALUES (%s, %s, %s, %s)""",
                (zoho_po_number, flag_type, full_description, datetime.datetime.now())
            )

            self.conn.commit()
            return True

        except Exception as e:
            log_error(f"Error raising flag: {str(e)}")
            if self.conn:
                self.conn.rollback()
            return False


    def fetch_po_from_zoho(self, po_number, receipt_id=None):
        """
        Fetch purchase order details from Zoho API and format it for storage.
        
        Args:
            po_number (str): The PO number to fetch
            receipt_id (int, optional): ID of receipt requesting this PO
            
        Returns:
            dict: Formatted PO data or None if failed
        """
        try:
            # from api import get_purchase_order_by_number

            log_info(f"Fetching PO {po_number} from Zoho")
            po_data = self.get_purchase_order_by_number(po_number)

            if not po_data:
                log_error(f"PO {po_number} not found in Zoho")
                self._raise_flag(
                    po_number,
                    "PO_NOT_FOUND",
                    f"Purchase order {po_number} not found in Zoho API",
                    receipt_id
                )
                return None

            # Format the PO data to match our expected structure
            formatted_po = {
                "zoho_po_number": po_number,
                "items": []
            }

            # Extract line items from PO
            for item in po_data.get("line_items", []):
                formatted_po["items"].append({
                    "description": item.get("description", ""),
                    "quantity": item.get("quantity", 0),
                    "original_quantity": item.get("quantity", 0),
                    "unit_price": item.get("rate", 0)
                })

            log_info(
                f"Successfully converted PO {po_number} to required format")
            return formatted_po

        except Exception as e:
            log_error(f"Error fetching PO {po_number} from Zoho: {str(e)}")
            self._raise_flag(
                po_number,
                "PO_FETCH_ERROR",
                f"Error fetching purchase order: {str(e)}",
                receipt_id
            )
            traceback.print_exc()
            return None

    def test_connection(self):
        """Test the database connection."""
        try:
            if self._ensure_connection():
                self.cursor.execute("SELECT current_timestamp")
                timestamp = self.cursor.fetchone()[0]
                print(
                    f"Successfully connected to database. Server time: {timestamp}")
                return True
            else:
                print("Failed to connect to database")
                return False
        except Exception as e:
            print(f"Connection test error: {str(e)}")
            traceback.print_exc()
            return False

    def check_po_status_in_zoho(self, po_number):
        """
        Check the status of a purchase order in Zoho.
        
        Args:
            po_number (str): The PO number to check
            
        Returns:
            tuple: (is_draft, status) - whether the PO is in draft status and the actual status
        """
        try:
            # from api import get_purchase_order_by_number

            log_info(f"Checking status of PO {po_number} in Zoho")
            po_data = self.get_purchase_order_by_number(po_number)

            if not po_data:
                log_error(f"PO {po_number} not found in Zoho")
                return False, "not_found"

            status = po_data.get("status", "unknown").lower()
            log_info(f"PO {po_number} has status: {status}")

            # Check if PO is in draft status or any other status
            is_draft = status == "draft"

            return is_draft, status

        except Exception as e:
            log_error(f"Error checking PO status: {str(e)}")
            traceback.print_exc()
            return False, "error"
        
    def process_receipt(self, receipt):
        """Process a receipt and store it in the database."""
        try:
            if not self._ensure_connection():
                log_error("Database connection failed")
                return

            zoho_po_number = receipt.get("zoho_po_number")
            zoho_short = zoho_po_number[3:]  # Remove first 3 characters of PO number
            
            items = receipt.get("items", [])

            log_info(f"Processing receipt for PO {zoho_po_number}")

            # Store the receipt (using zoho_short instead of zoho_po_number)
            self.cursor.execute(
                """INSERT INTO "ReceiptTable" (zoho_po_number, items, status, created_at) 
                VALUES (%s, %s, %s, %s) RETURNING receipt_id""",
                (zoho_short, json.dumps(items),
                'excess', datetime.datetime.now())
            )
            receipt_id = self.cursor.fetchone()[0]
            self.conn.commit()

            # Check if PO exists in cache (using zoho_short)
            self.cursor.execute(
                """SELECT * FROM "DecrementCache" WHERE zoho_po_number = %s""",
                (zoho_short,)
            )
            po_in_cache = self.cursor.fetchone()

            # If PO doesn't exist in cache, fetch it directly
            if not po_in_cache:
                log_info(f"PO {zoho_short} not found in cache, fetching from Zoho")

                # Check if PO is in ThreeWayValidator
                self.cursor.execute(
                    """SELECT * FROM "ThreeWayValidator" WHERE zoho_po_number = %s""",
                    (zoho_short,)
                )
                validator_record = self.cursor.fetchone()

                if not validator_record:
                    log_info(f"PO {zoho_short} not found in ThreeWayValidator, fetching from Zoho")
                    
                # Fetch PO from Zoho directly without checking status
                po_data = self.fetch_po_from_zoho(zoho_po_number, receipt_id)

                if po_data:
                    # Store PO in cache (using zoho_short)
                    self.cursor.execute(
                        """INSERT INTO "DecrementCache" (zoho_po_number, original_items, remaining_items, created_at, updated_at) 
                        VALUES (%s, %s, %s, %s, %s)""",
                        (zoho_short, json.dumps(po_data["items"]), json.dumps(po_data["items"]),
                        datetime.datetime.now(), datetime.datetime.now())
                    )
                    self.conn.commit()
                    log_info(f"Stored PO {zoho_short} in decrement cache")
                else:
                    log_error(f"Unable to process receipt - PO {zoho_short} could not be fetched")
                    return receipt_id

            # Process the receipt against the PO
            self.match_receipt_with_bills(receipt_id, zoho_short)
            return receipt_id

        except Exception as e:
            log_error(f"Error processing receipt: {str(e)}")
            traceback.print_exc()
            if self.conn:
                self.conn.rollback()
            return None

    def match_receipt_with_bills(self, receipt_id, zoho_po_number):
        """Match a receipt with its corresponding bills and update quantities."""
        try:
            if not self._ensure_connection():
                log_error("Database connection failed")
                return

            log_info(f"Matching receipt {receipt_id} with PO {zoho_po_number}")

            # Get receipt details
            self.cursor.execute(
                """SELECT * FROM "ReceiptTable" WHERE receipt_id = %s""",
                (receipt_id,)
            )
            receipt = self.cursor.fetchone()

            if not receipt:
                log_info(f"Receipt {receipt_id} not found in database")
                return

            # Get matching PO using zoho_po_number
            self.cursor.execute(
                """SELECT * FROM "DecrementCache" WHERE zoho_po_number = %s""",
                (zoho_po_number,)
            )
            bills = self.cursor.fetchall()

            if not bills:
                log_info(f"No matching PO found for {zoho_po_number}")
                return

            # Process each matching bill
            # Handle both JSON string and direct Python object
            receipt_items = receipt["items"]
            if isinstance(receipt_items, str):
                receipt_items = json.loads(receipt_items)

            receipt_fully_used = False

            for bill in bills:
                if receipt_fully_used:
                    break

                # Use remaining_items instead of items
                remaining_items = bill["remaining_items"]
                if isinstance(remaining_items, str):
                    remaining_items = json.loads(remaining_items)

                # Decrement bill quantities using receipt items
                result = self._decrement_bill_quantities(
                    remaining_items, receipt_items)
                updated_items = result["updated_items"]
                fully_decremented = result["is_fully_decremented"]
                excess_items = result.get("excess_items", [])

                if fully_decremented:
                    # Delete from cache
                    self.cursor.execute(
                        """DELETE FROM "DecrementCache" WHERE zoho_po_number = %s""",
                        (bill["zoho_po_number"],)
                    )

                    # Handle PO validation and system updates
                    self._handle_fully_decremented_po(
                        zoho_po_number, excess_items, receipt_id)

                    log_info(
                        f"PO {zoho_po_number} fully decremented and finalized")
                else:
                    # Update PO with decremented quantities
                    self.cursor.execute(
                        """UPDATE "DecrementCache" SET remaining_items = %s, updated_at = %s 
                        WHERE zoho_po_number = %s""",
                        (json.dumps(updated_items),
                         datetime.datetime.now(), bill["zoho_po_number"])
                    )
                    log_info(
                        f"PO {zoho_po_number} partially decremented with receipt {receipt_id}")

                    # If there were excess items but PO is not fully decremented
                    if excess_items and len(excess_items) > 0:
                        excess_json = json.dumps(excess_items)
                        self._raise_flag(
                            zoho_po_number,
                            "EXCESS_ITEMS_RECEIVED",
                            f"Received more items than ordered in PO: {excess_json}",
                            receipt_id
                        )

            # Update receipt status
            self.cursor.execute(
                """UPDATE "ReceiptTable" SET status = 'cleared' WHERE receipt_id = %s""",
                (receipt_id,)
            )

            self.conn.commit()

        except Exception as e:
            log_error(f"Error matching receipt with bills: {str(e)}")
            traceback.print_exc()
            if self.conn:
                self.conn.rollback()

    def _handle_fully_decremented_po(self, zoho_po_number, excess_items=None, receipt_id=None):
        """
        Handle a PO that has been fully decremented.
        
        Args:
            zoho_po_number (str): The PO number that's fully decremented
            excess_items (list, optional): List of items received in excess
            receipt_id (int, optional): Receipt ID that caused full decrement
        """
        try:
            log_info(f"PO {zoho_po_number} has been fully decremented")

            # No need to convert PO number anymore - use it directly as text
            # Check if this PO already exists in ThreeWayValidator
            self.cursor.execute(
                """SELECT * FROM "ThreeWayValidator" WHERE zoho_po_number = %s""",
                (zoho_po_number,)
            )
            existing_validator = self.cursor.fetchone()

            current_time = datetime.datetime.now()
            both_validations_complete = False

            if existing_validator:
                # Update receipt status and get current invoice_status
                self.cursor.execute(
                    """UPDATE "ThreeWayValidator" SET receipt_status = TRUE, updated_at = %s
                    WHERE zoho_po_number = %s RETURNING invoice_status""",
                    (current_time, zoho_po_number)
                )
                result = self.cursor.fetchone()
                invoice_status = result[0] if result else False
                # Since we just set receipt_status to TRUE
                both_validations_complete = invoice_status

                log_info(
                    f"Updated ThreeWayValidator for PO {zoho_po_number} - receipt_status=TRUE, invoice_status={invoice_status}")
            else:
                # Create new record with receipt_status=TRUE, invoice_status=FALSE
                self.cursor.execute(
                    """INSERT INTO "ThreeWayValidator" 
                    (zoho_po_number, invoice_status, receipt_status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (zoho_po_number, False, True, current_time, current_time)
                )
                both_validations_complete = False  # New record, so invoice_status is FALSE

                log_info(
                    f"Created ThreeWayValidator for PO {zoho_po_number} - receipt_status=TRUE, invoice_status=FALSE")

            # Add to system logs
            self.cursor.execute(
                """INSERT INTO "SystemLogs" 
                (log_type, zoho_po_number, attachment, log_message, created_at)
                VALUES (%s, %s, %s, %s, %s)""",
                ('Warehouse_Log', zoho_po_number, json.dumps({}),
                 f"PO {zoho_po_number} has been fully validated by warehouse receipts",
                 current_time)
            )
            log_info(f"Added system log for PO {zoho_po_number} validation")

            # Submit PO for approval in Zoho ONLY if both validations are complete
            if both_validations_complete:
                log_info(
                    f"Both receipt and invoice validations complete for PO {zoho_po_number}, submitting for approval")
                po_short = "PO-"+zoho_po_number  # Remove first 3 characters of PO number
                bill_id = self.get_bill_id(po_short)
                po_short = zoho_po_number[3:]
                submit_bill_for_approval(bill_id,po_short)
            else:
                log_info(
                    f"Receipt validation complete for PO {zoho_po_number}, waiting for invoice validation")

            # If there were excess items, raise flags for them
            if excess_items and len(excess_items) > 0:
                excess_json = json.dumps(excess_items)
                self._raise_flag(
                    zoho_po_number,
                    "EXCESS_ITEMS_RECEIVED",
                    f"Received more items than ordered in PO: {excess_json}",
                    receipt_id
                )

            self.conn.commit()

        except Exception as e:
            log_error(f"Error handling fully decremented PO: {str(e)}")
            traceback.print_exc()
            if self.conn:
                self.conn.rollback()


    def _decrement_bill_quantities(self, bill_items, receipt_items):
        """
        Decrement bill quantities based on received quantities.
        
        Args:
            bill_items (list): List of bill items with quantities
            receipt_items (list): List of receipt items with quantities
            
        Returns:
            dict: Updated bill items, decrementation status and excess items
        """
        updated_items = []
        total_remaining = 0
        excess_items = []

        # Create lookup for receipt items by description
        receipt_lookup = {}
        for item in receipt_items:
            receipt_lookup[item["description"]] = item["quantity"]

        # Process each bill item
        for bill_item in bill_items:
            description = bill_item["description"]
            received_qty = receipt_lookup.get(description, 0)

            # Decrement the quantity
            new_quantity = bill_item["quantity"] - received_qty

            # Check if we've received more than ordered - ONLY if item is in current receipt
            if new_quantity < 0 and received_qty > 0:
                excess_quantity = abs(new_quantity)
                excess_items.append({
                    "description": description,
                    "excess_quantity": excess_quantity,
                    "ordered_quantity": bill_item.get("original_quantity", bill_item["quantity"])
                })
                log_info(
                    f"Excess received for '{description}': Ordered {bill_item.get('original_quantity', bill_item['quantity'])}, received extra {excess_quantity}")

            # For total remaining, ignore negative values (don't subtract from the total)
            total_remaining += max(0, new_quantity)

            # Add to updated items list - keeping negative quantities to track excess
            updated_items.append({
                "description": description,
                "quantity": new_quantity,
                "original_quantity": bill_item.get("original_quantity", bill_item["quantity"]),
                "received_quantity": bill_item.get("received_quantity", 0) + received_qty
            })

            # Log the decrement
            log_info(
                f"Item '{description}': Decremented {received_qty} units, remaining: {new_quantity}")

        # Check if bill is fully decremented (all items have been received)
        # We consider it fully decremented if no item has a positive quantity
        has_positive_qty = any(item["quantity"] > 0 for item in updated_items)
        is_fully_decremented = not has_positive_qty

        if is_fully_decremented:
            log_info("All items in bill have been received (fully decremented)")
        else:
            log_info(f"Bill still has {total_remaining} units pending receipt")

        return {
            "updated_items": updated_items,
            "is_fully_decremented": is_fully_decremented,
            "excess_items": excess_items
        }
    def get_purchase_order_by_number(self,po_number):
        """
        Fetch a specific purchase order by its number directly from Zoho API.
        Always fetches the latest data with no caching.
        """
        # First get the purchase order ID
        endpoint = f"{config.ZOHO_API_DOMAIN}/books/v3/purchaseorders?organization_id={config.ZOHO_ORG_ID}&purchaseorder_number={po_number}"
        headers = get_auth_headers()
        headers['Cache-Control'] = 'no-cache, no-store'  # Prevent caching

        try:
            print(f"Fetching PO list for number: {po_number}")
            response = requests.get(endpoint, headers=headers)
            print("HTTP Status:", response.status_code, response.reason)

            if response.status_code == 200:
                data = response.json()
                purchaseorders = data.get("purchaseorders", [])
                if purchaseorders:
                    po_id = purchaseorders[0].get("purchaseorder_id")
                    if po_id:
                        # Now get the full details with a separate request
                        details_endpoint = f"{config.ZOHO_API_DOMAIN}/books/v3/purchaseorders/{po_id}?organization_id={config.ZOHO_ORG_ID}"
                        print(f"Fetching detailed PO data for ID: {po_id}")
                        details_response = requests.get(
                            details_endpoint, headers=headers)

                        if details_response.status_code == 200:
                            details_data = details_response.json()
                            return details_data.get("purchaseorder")
                        else:
                            print(
                                f"Error fetching PO details: {details_response.status_code} - {details_response.text}")

                print(f"No purchase order found with number: {po_number}")
                return None
            else:
                print(
                    f"Error querying POs: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception during API request: {str(e)}")
            return None
    def submit_po_for_approval(self, zoho_po_number):
        """
        Submit a purchase order for approval in Zoho.
        
        Args:
            zoho_po_number (str): The PO number to submit
            
        Returns:
            bool: True if successfully submitted, False otherwise
        """
        try:
            # First, get the internal Zoho ID for this PO number
            # from api import get_purchase_order_by_number

            log_info(f"Looking up internal ID for {zoho_po_number}")
            po_data = self.get_purchase_order_by_number(zoho_po_number)

            # Check different possible field names for the ID
            internal_po_id = None
            possible_id_fields = [
                "purchase_order_id", "purchaseorder_id", "id"]

            for field in possible_id_fields:
                if po_data and field in po_data:
                    internal_po_id = po_data[field]
                    break

            if not internal_po_id:
                log_error(
                    f"Could not find Zoho internal ID for {zoho_po_number}")
                return False

            log_info(
                f"Found internal ID {internal_po_id} for {zoho_po_number}")

            # Get auth headers using token manager
            headers = get_auth_headers()
            if not headers:
                log_error(f"Failed to get authentication headers for Zoho API")
                return False

            # Make API request to submit PO for approval
            org_id = config.ZOHO_ORG_ID
            api_domain = "https://www.zohoapis.in"  # Make sure this matches your region

            url = f"{api_domain}/books/v3/purchaseorders/{internal_po_id}/submit"
            params = {"organization_id": org_id}

            log_info(
                f"Submitting {zoho_po_number} (ID: {internal_po_id}) for approval in Zoho")
            response = requests.post(url, headers=headers, params=params)

            if response.status_code == 200 or response.status_code == 201:
                response_data = response.json()
                if response_data.get("code") == 0:
                    log_info(
                        f"✅ SUCCESS: PO {zoho_po_number} is now in PENDING APPROVAL state in Zoho")
                    log_info(
                        f"Successfully submitted {zoho_po_number} for approval")
                    return True

            log_error(
                f"Failed to submit {zoho_po_number} for approval. Status: {response.status_code}, Response: {response.text}")
            return False

        except Exception as e:
            log_error(
                f"Error submitting {zoho_po_number} for approval: {str(e)}")
            traceback.print_exc()
            return False
    def get_bill_id(self, po_number):
        """
        Retrieve the Zoho Bill ID using the given PO number.
        """
        try:
            if not self._ensure_connection():
                return None  # Return None if DB connection fails

            query = """
                SELECT zoho_bill_id 
                FROM "InvoiceStore" 
                WHERE zoho_po_number = %s;
            """
            
            self.cursor.execute(query, (po_number,))
            bill_id = self.cursor.fetchone()  # Fetch a single result

            if bill_id:
                log_info(f"✅ Retrieved Bill ID {bill_id[0]} for PO {po_number}")
                return bill_id[0]  # Return actual ID value
            else:
                log_info(f"⚠️ No Bill ID found for PO {po_number}")
                return None

        except Exception as e:
            log_error(f"❌ Error retrieving bill ID: {str(e)}")
            traceback.print_exc()
            return None
    def get_bill_status(self, zoho_bill_id):
        """
        Get the current status of a bill and its remaining quantities.
        
        Args:
            zoho_bill_id (str): The bill ID to check
            
        Returns:
            dict: Bill status information
        """
        try:
            if not self._ensure_connection():
                return {"error": "Database connection failed"}

            # For backwards compatibility, try using zoho_bill_id as zoho_po_number
            zoho_po_number = zoho_bill_id

            self.cursor.execute(
                """SELECT * FROM "DecrementCache" WHERE zoho_po_number = %s""",
                (zoho_po_number,)
            )

            po_data = self.cursor.fetchone()

            if not po_data:
                return {
                    "zoho_bill_id": zoho_bill_id,
                    "status": "fully_matched_or_not_found",
                    "in_cache": False,
                    "items": []
                }

            # Get original and remaining items
            original_items = po_data["original_items"]
            if isinstance(original_items, str):
                original_items = json.loads(original_items)

            remaining_items = po_data["remaining_items"]
            if isinstance(remaining_items, str):
                remaining_items = json.loads(remaining_items)

            total_remaining = sum(max(0, item.get("quantity", 0))
                                  for item in remaining_items)

            return {
                "zoho_bill_id": zoho_bill_id,  # Keep for backward compatibility
                "zoho_po_number": po_data["zoho_po_number"],
                "status": "in_decrement_cache",
                "created_at": po_data["created_at"].isoformat(),
                "updated_at": po_data["updated_at"].isoformat(),
                "in_cache": True,
                "original_items": original_items,
                "remaining_items": remaining_items,
                "total_remaining": total_remaining
            }

        except Exception as e:
            log_error(f"Error getting bill status: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}

    def get_receipt_status(self, receipt_id):
        """
        Get the current status of a receipt.
        
        Args:
            receipt_id (int): The receipt ID to check
            
        Returns:
            dict: Receipt status information
        """
        try:
            if not self._ensure_connection():
                return {"error": "Database connection failed"}

            self.cursor.execute(
                """SELECT * FROM "ReceiptTable" WHERE receipt_id = %s""",
                (receipt_id,)
            )

            receipt = self.cursor.fetchone()

            if not receipt:
                return {"error": "Receipt not found"}

            items = receipt["items"]
            if isinstance(items, str):
                items = json.loads(items)
            return {
                "receipt_id": receipt["receipt_id"],
                "zoho_po_number": receipt["zoho_po_number"],
                "status": receipt["status"],
                "created_at": receipt["created_at"].isoformat(),
                "updated_at": receipt["updated_at"].isoformat(),
                "items": items
            }

        except Exception as e:
            log_error(f"Error getting receipt status: {str(e)}")
            return {"error": str(e)}

    def __del__(self):
        """Clean up database connections when object is deleted."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


# Example usage
# Example usage
if __name__ == "__main__":
    validator = InventoryValidator()
    validator.test_connection()
    
    # Process receipts from file
    try:
        with open('/Users/kriti.bharadwaj03/digitalInvoiceProcessing/Akaunting/data/receipts.json', 'r') as f:
            receipts_data = json.load(f)

        # Handle both list and single object formats
        if isinstance(receipts_data, dict) and "zoho_po_number" in receipts_data:
            receipts_data = [receipts_data]

        print(f"\nProcessing {len(receipts_data)} receipts from receipts.json")

        for receipt in receipts_data:
            print(
                f"\n=== Processing receipt for PO {receipt.get('zoho_po_number')} ===")
            receipt_id = validator.process_receipt(receipt)

            if receipt_id:
                print(f"Receipt processed successfully with ID: {receipt_id}")

                # Get updated PO status
                status = validator.get_bill_status(
                    receipt.get('zoho_po_number'))
                print(f"Updated PO status: {json.dumps(status, indent=2)}")
            else:
                print("Failed to process receipt")

    except FileNotFoundError:
        print("receipts.json file not found. Using example receipt.")
        # Example receipt
        receipt1 = {
            "zoho_po_number": "PO-2023-001",
            "items": [
                {
                    "description": "Office Chair - Premium",
                    "quantity": 2
                }
            ]
        }

        validator.process_receipt(receipt1)
        print("\n=== After processing receipt ===")
        status = validator.get_bill_status("PO-2023-001")
        print(f"PO status: {json.dumps(status, indent=2)}")

