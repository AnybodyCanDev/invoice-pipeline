import json
import datetime
import psycopg2
import psycopg2.extras
import requests
import traceback
from Akaunting.utils.logger import log_info, log_error
from Akaunting.token_manager import get_auth_headers
import config



class InventoryValidator:
    def __init__(self):
        """Initialize the inventory validator with database configuration."""
        self.db_url = "postgresql://neondb_owner:npg_EY4dmMAPZ6bN@ep-cool-butterfly-a5mk6awz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
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
    def insert_invoice(self, invoice_data, email_id):
        """Update InvoiceStore with extracted invoice data."""
        try:
            if not self._ensure_connection():
                return

            query = """
                UPDATE "InvoiceStore" 
                SET 
                    zoho_po_number = %s,
                    scanned_data = %s::jsonb
                WHERE 
                    invoice_id = %s;
            """
            
            for invoice in invoice_data["invoices"]:
                bill_number = invoice.get("bill_number", "UNKNOWN")  # Extract bill_number
                invoice_id = email_id  # Match using email_id
                
                self.cursor.execute(
                    query,
                    (
                        bill_number,  # Update zoho_po_number with bill_number
                        json.dumps(invoice),  # Store full invoice as JSON
                        invoice_id  # Match on invoice_id (email_id)
                    ),
                )
            
            self.conn.commit()
            log_info("Invoice data updated successfully in InvoiceStore")
        
        except Exception as e:
            log_error(f"Error updating invoice data: {str(e)}")
            traceback.print_exc()


    def insert_invoice_s3(self, new_entry):
        """Insert S3 invoice data into the InvoiceStore table."""
        try:
            if not self._ensure_connection():
                return
            
            # Using lowercase table name
            query = """
            INSERT INTO "InvoiceStore" (
                invoice_id,
                s3_url,
                created_at
            ) VALUES (
                %s, %s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (invoice_id) DO UPDATE SET 
                s3_url = EXCLUDED.s3_url;
            """
            
            self.cursor.execute(
                query,
                (
                    new_entry["email_id"],  # Use email_id as invoice_id
                    new_entry["s3_path"],   # Use s3_path as s3_url
                ),
            )
            
            self.conn.commit()
            log_info("Invoice S3 data inserted successfully into InvoiceStore")
        
        except Exception as e:
            log_error(f"Error inserting S3 invoice data: {str(e)}")
            traceback.print_exc()
            
    def insert_bill_id(self, bill_id, email_id):
        """Update InvoiceStore with extracted invoice data."""
        try:
            if not self._ensure_connection():
                return

            query = """
                UPDATE "InvoiceStore" 
                SET zoho_bill_id = %s
                WHERE invoice_id = %s;
            """
            
            self.cursor.execute(
                query,
                (bill_id, email_id),  # Use email_id to match invoice_id
            )
            
            self.conn.commit()
            log_info("Bill id updated successfully in InvoiceStore")

        except Exception as e:
            log_error(f"Error updating bill id: {str(e)}")
            traceback.print_exc()
            
    def update_or_insert_invoice_status(self, zoho_po_number):
        """Update invoice_status if record exists, otherwise insert a new row.
        After updating, check if receipt_status is also TRUE.
        """
        try:
            if not self._ensure_connection():
                return

            query = """
                INSERT INTO "ThreeWayValidator" (
                    zoho_po_number, invoice_status, receipt_status, updated_at
                ) VALUES (
                    %s, TRUE, FALSE, CURRENT_TIMESTAMP
                ) ON CONFLICT (zoho_po_number) 
                DO UPDATE 
                SET 
                    invoice_status = TRUE, 
                    updated_at = CURRENT_TIMESTAMP
                RETURNING receipt_status;
            """
            po_number_str = zoho_po_number[3:]

            self.cursor.execute(query, (po_number_str,))
            self.conn.commit()

            # Fetch the receipt_status after updating
            receipt_status = self.cursor.fetchone()[0]  # Fetch first column of the result
            
            log_info(f"Updated or inserted invoice_status for zoho_po_number: {zoho_po_number}")

            # Check if receipt_status is TRUE
            if receipt_status:
                log_info(f"✅ Three-way match complete for {zoho_po_number} (Both invoice and receipt recorded).")
                return receipt_status
            else:
                log_info(f"⚠️ Awaiting receipt for {zoho_po_number}.")

        except Exception as e:
            log_error(f"Error updating or inserting invoice status: {str(e)}")
            traceback.print_exc()

    def log_to_system(self, log_type, zoho_po_number, attachment, log_message):
        """
        Store logs in the SystemLogs table.
        
        Parameters:
        - log_type: String (e.g., 'invoice', 'receipt', 'error')
        - zoho_po_number: Int (PO number from Zoho)
        - attachment: Dict (will be stored as JSON)
        - log_message: String (descriptive message about the log)
        
        Returns:
        - Boolean: True if successful, False otherwise
        """
        try:
            if not self._ensure_connection():
                return False
                
            query = """
                INSERT INTO "SystemLogs" 
                (log_type, zoho_po_number, attachment, log_message)
                VALUES (%s, %s, %s::jsonb, %s)
                RETURNING log_id;
            """
            
            self.cursor.execute(
                query,
                (
                    log_type,
                    zoho_po_number,
                    json.dumps(attachment),
                    log_message
                ),
            )
            
            log_id = self.cursor.fetchone()[0]
            self.conn.commit()
            
            print(f"Log entry created successfully with ID: {log_id}")
            return True
            
        except Exception as e:
            print(f"Error creating log entry: {str(e)}")
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


        


                

            

