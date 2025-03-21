import streamlit as st
import psycopg2
import psycopg2.extras
import datetime
import uuid
import hashlib
import os
from datetime import datetime
import subprocess
# Set page configuration
st.set_page_config(
    page_title="Invoice Approval Dashboard",
    page_icon="📝",
    layout="wide"
)

# Database connection
DB_URL = "postgresql://neondb_owner:npg_EY4dmMAPZ6bN@ep-cool-butterfly-a5mk6awz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    """Establish a database connection."""
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {str(e)}")
        return None

def authenticate_user(emp_id, password):
    """Authenticate a user using credentials from the Auth table."""
    conn = get_db_connection()
    if not conn:
        return False, None
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get password hash from database
        cursor.execute("SELECT password FROM \"Auth\" WHERE emp_id = %s", (emp_id,))
        result = cursor.fetchone()
        
        if not result:
            return False, None
        
        stored_password = result["password"]
        
        # In a real app, you'd use password hashing
        # For this demo we'll do simple comparison
        if password == stored_password:
            # Get user details
            cursor.execute("SELECT * FROM \"Employee\" WHERE emp_id = %s", (emp_id,))
            user_data = cursor.fetchone()
            return True, dict(user_data)
        else:
            return False, None
            
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return False, None
    finally:
        conn.close()

def get_pending_approvals(emp_id):
    """Get all pending approvals for the employee."""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        query = """
        SELECT a.approval_id, a.invoice_id, a.created_at, a.approval_level, a.category,
               e.emp_name as requester_name
        FROM "Approval" a
        JOIN "Employee" e ON a.emp_id = e.emp_id
        WHERE a.emp_id = %s AND a.approved_at IS NULL
        ORDER BY a.created_at DESC
        """
        
        cursor.execute(query, (emp_id,))
        approvals = cursor.fetchall()
        return [dict(approval) for approval in approvals]
            
    except Exception as e:
        st.error(f"Error fetching approvals: {str(e)}")
        return []
    finally:
        conn.close()

def approve_invoice(approval_id, emp_id):
    """Approve an invoice and create next level approval if needed."""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Start a transaction
        conn.autocommit = False
        
        # First, get current approval details
        cursor.execute(
            """SELECT a.*, e.sup_id 
               FROM "Approval" a
               JOIN "Employee" e ON a.emp_id = e.emp_id
               WHERE a.approval_id = %s""", 
            (approval_id,)
        )
        approval = cursor.fetchone()
        
        if not approval:
            conn.rollback()
            return False, "Approval not found"
        
        # Update current approval
        cursor.execute(
            """UPDATE "Approval" 
               SET approved_at = CURRENT_TIMESTAMP 
               WHERE approval_id = %s""",
            (approval_id,)
        )
        
        # If this is level 1, create a level 2 approval for supervisor
        if approval["approval_level"] == 1 and approval["sup_id"]:
            new_approval_id = str(uuid.uuid4())
            
            cursor.execute(
                """INSERT INTO "Approval" 
                   (approval_id, invoice_id, emp_id, created_at, approval_level, category)
                   VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 2, %s)""",
                (new_approval_id, approval["invoice_id"], approval["sup_id"], approval["category"])
            )
        if approval["approval_level"] == 2:
            subprocess.run(["python", "/Users/kriti.bharadwaj03/digitalInvoiceProcessing/Akaunting/approval_to_approved.py", approval["invoice_id"]], check=True)          
        
        # Commit the transaction
        conn.commit()
        return True, "Invoice approved successfully"
        
    except Exception as e:
        conn.rollback()
        return False, f"Error approving invoice: {str(e)}"
    finally:
        conn.close()

def raise_flag(zoho_po_number, flag_type, flag_description):
    """
    Add a flag entry to the RaiseFlags table
    
    Args:
        zoho_po_number (str): The PO number from Zoho
        flag_type (str): Type of flag being raised
        flag_description (str): Description of the flag
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Insert the flag into the RaiseFlags table
        insert_query = """
        INSERT INTO "RaiseFlags" (zoho_po_number, flag_type, flag_description, created_at)
        VALUES (%s, %s, %s, %s) RETURNING flag_id;
        """
        
        current_time = datetime.now()
        cursor.execute(insert_query, (zoho_po_number, flag_type, flag_description, current_time))
        flag_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        
        st.success(f"Flag raised successfully for PO {zoho_po_number}. Flag ID: {flag_id}")
        return True
        
    except Exception as e:
        st.error(f"Failed to raise flag for PO {zoho_po_number}. Error: {str(e)}")
        return False
    finally:
        conn.close()

def deny_invoice(approval_id, emp_id, denial_reason=""):
    """Deny an invoice approval and raise a flag."""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Start a transaction
        conn.autocommit = False
        
        # First, get current approval details and employee name
        cursor.execute(
            """SELECT a.*, e.emp_name 
               FROM "Approval" a
               JOIN "Employee" e ON a.emp_id = e.emp_id
               WHERE a.approval_id = %s""", 
            (approval_id,)
        )
        approval = cursor.fetchone()
        
        if not approval:
            conn.rollback()
            return False, "Approval not found"
        
        # Mark the approval as denied (we'll use the approved_at field but add a status field in a real app)
        cursor.execute(
            """UPDATE "Approval" 
               SET approved_at = CURRENT_TIMESTAMP, 
                   status = 'denied'
               WHERE approval_id = %s""",
            (approval_id,)
        )
        
        # Create the flag description
        approver_name = approval["emp_name"]
        if denial_reason.strip():
            flag_description = f"Denied by {approver_name}. Reason: {denial_reason}"
        else:
            flag_description = f"Denied by {approver_name}"
        
        # Commit the transaction to update the approval status
        conn.commit()
        
        # Now raise the flag (separate connection to avoid transaction issues)
        flag_raised = raise_flag(
            zoho_po_number=approval["invoice_id"],  # Using invoice_id as PO number
            flag_type="invoice denied approval",
            flag_description=flag_description
        )
        
        if flag_raised:
            return True, "Invoice denied successfully"
        else:
            return False, "Invoice marked as denied but flag raising failed"
        
    except Exception as e:
        conn.rollback()
        return False, f"Error denying invoice: {str(e)}"
    finally:
        conn.close()

def render_login_page():
    """Render the login page."""
    st.title("Invoice Approval Dashboard")
    
    with st.form("login_form"):
        emp_id = st.text_input("Employee ID")
        password = st.text_input("Password", type="password")
        
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if not emp_id or not password:
                st.error("Please enter both employee ID and password")
                return
                
            success, user_data = authenticate_user(emp_id, password)
            
            if success:
                st.session_state["logged_in"] = True
                st.session_state["user"] = user_data
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid employee ID or password")

def render_dashboard(user):
    """Render the main dashboard for an authenticated user."""
    st.title(f"Welcome, {user['emp_name']}")
    st.subheader("Invoice Approval Dashboard")
    
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()
        
    # Display pending approvals
    st.subheader("Pending Approvals")
    
    pending_approvals = get_pending_approvals(user["emp_id"])
    
    if not pending_approvals:
        st.info("You have no pending approvals.")
    else:
        for approval in pending_approvals:
            with st.expander(f"Invoice: {approval['invoice_id']} - {approval['category']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Approval ID:** {approval['approval_id']}")
                    st.write(f"**Invoice ID:** {approval['invoice_id']}")
                    st.write(f"**Category:** {approval['category']}")
                
                with col2:
                    st.write(f"**Requested by:** {approval['requester_name']}")
                    st.write(f"**Created at:** {approval['created_at']}")
                    st.write(f"**Approval Level:** {approval['approval_level']}")
                
                # Create two columns for Approve and Deny buttons
                action_col1, action_col2 = st.columns(2)
                
                with action_col1:
                    if st.button("Approve", key=f"approve_{approval['approval_id']}"):
                        success, message = approve_invoice(approval['approval_id'], user['emp_id'])
                        
                        if success:
                            st.success(message)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(message)
                
                with action_col2:
                    if st.button("Deny", key=f"deny_{approval['approval_id']}"):
                        # Show denial reason input when deny button is clicked
                        st.session_state[f"show_deny_reason_{approval['approval_id']}"] = True
                
                # Show denial reason input if deny button was clicked
                if st.session_state.get(f"show_deny_reason_{approval['approval_id']}", False):
                    denial_reason = st.text_area(
                        "Reason for denial (optional)", 
                        key=f"denial_reason_{approval['approval_id']}"
                    )
                    
                    if st.button("Confirm Denial", key=f"confirm_deny_{approval['approval_id']}"):
                        success, message = deny_invoice(
                            approval['approval_id'], 
                            user['emp_id'],
                            denial_reason
                        )
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    
                    if st.button("Cancel", key=f"cancel_deny_{approval['approval_id']}"):
                        del st.session_state[f"show_deny_reason_{approval['approval_id']}"]
                        st.rerun()

# Main app
def main():
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        
    # Route to appropriate page
    if st.session_state["logged_in"]:
        render_dashboard(st.session_state["user"])
    else:
        render_login_page()

if __name__ == "__main__":
    main()