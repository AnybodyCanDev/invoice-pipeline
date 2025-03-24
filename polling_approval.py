import json
import datetime
import psycopg2
import psycopg2.extras
import time
import traceback
from Akaunting.utils.logger import log_info, log_error
from Akaunting.token_manager import get_auth_headers
import config

class ApprovalPoller:
    def __init__(self, poll_interval=5):
        """
        Initialize the approval poller with database configuration.
        
        Args:
            poll_interval (int): Time in seconds between each poll
        """
        self.db_url = "postgresql://neondb_owner:npg_EY4dmMAPZ6bN@ep-cool-butterfly-a5mk6awz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
        self.conn = None
        self.cursor = None
        self.poll_interval = poll_interval
        self.last_poll_time = None
        self._connect_db()

    def _connect_db(self):
        """Establish a database connection."""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor(
                cursor_factory=psycopg2.extras.DictCursor)
            print("Connected to database successfully")
            log_info("Connected to database successfully")
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            log_error(f"Error connecting to database: {str(e)}")
            traceback.print_exc()

    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if needed."""
        if not self.conn or self.conn.closed:
            self._connect_db()
        return self.conn and not self.conn.closed

    def _initialize_last_poll_time(self):
        """Initialize the last poll time to current time."""
        if not self.last_poll_time:
            self.last_poll_time = datetime.datetime.now()
            print(f"Initialized last poll time to {self.last_poll_time}")
            log_info(f"Initialized last poll time to {self.last_poll_time}")

    def check_for_changes(self):
        """
        Check for changes in the Approval table since the last poll.
        
        Returns:
            bool: True if changes were found and processed, False otherwise
        """
        try:
            if not self._ensure_connection():
                print("Database connection is not available")
                log_error("Database connection is not available")
                return False
            
            # Initialize last poll time if it's None
            self._initialize_last_poll_time()
            
            current_time = datetime.datetime.now()
            
            # Query for new or updated records since last poll
            self.cursor.execute("""
                SELECT * FROM "Approval" 
                WHERE created_at > %s OR approved_at > %s
                ORDER BY 
                    GREATEST(
                        COALESCE(created_at, '1970-01-01'::timestamp), 
                        COALESCE(approved_at, '1970-01-01'::timestamp)
                    ) ASC
                """, (self.last_poll_time, self.last_poll_time))
            
            changes = self.cursor.fetchall()
            
            # Process any changes found
            if changes:
                print(f"Found {len(changes)} changes since last poll")
                log_info(f"Found {len(changes)} changes since last poll")
                self.process_changes(changes)
            else:
                print("No changes found")
            
            # Update the last poll time
            self.last_poll_time = current_time
            return bool(changes)
        
        except Exception as e:
            print(f"Error checking for changes: {str(e)}")
            log_error(f"Error checking for changes: {str(e)}")
            traceback.print_exc()
            return False

    def process_changes(self, changes):
        """
        Process changes found in the Approval table.
        
        Args:
            changes (list): List of changed records from the Approval table
        """
        try:
            for record in changes:
                approval_id = record['approval_id']
                status = record['status']
                approval_level = record['approval_level']
                invoice_id = record['invoice_id']
                
                print(f"Processing change for approval_id: {approval_id}, status: {status}")
                log_info(f"Processing change for approval_id: {approval_id}, status: {status}")
                
                # Based on the status, call the appropriate handler
                if status == 'approved':
                    self._handle_approved_status(record)
                elif status == 'rejected':
                    self._handle_rejected_status(record)
                elif status == 'pending':
                    self._handle_pending_status(record)
                else:
                    print(f"Unknown status: {status} for approval_id: {approval_id}")
                    log_info(f"Unknown status: {status} for approval_id: {approval_id}")
                
        except Exception as e:
            print(f"Error processing changes: {str(e)}")
            log_error(f"Error processing changes: {str(e)}")
            traceback.print_exc()

    def _handle_approved_status(self, record):
        """
        Handle business logic when an approval is approved.
        
        Args:
            record (dict): The approved record
        """
        approval_id = record['approval_id']
        invoice_id = record['invoice_id']
        
        print(f"Approval {approval_id} for invoice {invoice_id} has been approved")
        log_info(f"Approval {approval_id} for invoice {invoice_id} has been approved")
        
        # Implement your business logic here
        # For example:
        # 1. Update related records
        # 2. Send notifications
        # 3. Trigger subsequent workflow steps

    def _handle_rejected_status(self, record):
        """
        Handle business logic when an approval is rejected.
        
        Args:
            record (dict): The rejected record
        """
        approval_id = record['approval_id']
        invoice_id = record['invoice_id']
        
        print(f"Approval {approval_id} for invoice {invoice_id} has been rejected")
        log_info(f"Approval {approval_id} for invoice {invoice_id} has been rejected")
        
        # Implement your rejection logic here

    def _handle_pending_status(self, record):
        """
        Handle business logic when an approval is pending.
        
        Args:
            record (dict): The pending record
        """
        approval_id = record['approval_id']
        invoice_id = record['invoice_id']
        
        print(f"Approval {approval_id} for invoice {invoice_id} is pending")
        log_info(f"Approval {approval_id} for invoice {invoice_id} is pending")
        
        # Implement your pending status logic here

    def start_polling(self):
        """Start polling for approval changes."""
        print(f"Starting approval polling with interval of {self.poll_interval} seconds...")
        log_info(f"Starting approval polling with interval of {self.poll_interval} seconds...")
        
        # Initialize the last poll time
        self._initialize_last_poll_time()
        
        try:
            while True:
                if self.check_for_changes():
                    print("Changes processed successfully")
                
                time.sleep(self.poll_interval)
        
        except KeyboardInterrupt:
            print("Polling stopped by user")
            log_info("Polling stopped by user")
        
        except Exception as e:
            print(f"Error in polling loop: {str(e)}")
            log_error(f"Error in polling loop: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    poller = ApprovalPoller(poll_interval=5)  # Poll every 5 seconds
    poller.start_polling()