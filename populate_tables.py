import psycopg2
import psycopg2.extras
import uuid
from datetime import datetime, timedelta

# Database connection string
DB_URL = "DATABASE_URL"

def populate_test_data():
    """Populate the database with test data for the invoice approval system."""
    conn = None
    try:
        # Connect to the database
        print("Connecting to the database...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Start transaction
        conn.autocommit = False
        
        # # Clear existing data (optional - comment out if you want to keep existing data)
        # print("Clearing existing test data...")
        # cursor.execute('DELETE FROM "Approval" WHERE invoice_id LIKE \'TEST-%\'')
        # cursor.execute('DELETE FROM "Auth" WHERE emp_id >= 1000')
        # cursor.execute('DELETE FROM "Employee" WHERE emp_id >= 1000')
        
        # Create test employees
        print("Creating test employees...")
        employees = [
            (1000, 'John Manager', 'john@example.com', 'Manager', 1100, 5),
            (1001, 'Alice Supervisor', 'alice@example.com', 'Supervisor', 1000, 10),
            (1002, 'Bob Supervisor', 'bob@example.com', 'Supervisor', 1000, 8),
            (1003, 'Carol Approver', 'carol@example.com', 'Approver', 1001, 15),
            (1004, 'Dave Approver', 'dave@example.com', 'Approver', 1001, 12),
            (1005, 'Eve Approver', 'eve@example.com', 'Approver', 1002, 14),
            (1006, 'Frank Approver', 'frank@example.com', 'Approver', 1002, 11),
        ]
        
        for emp in employees:
            cursor.execute(
                '''INSERT INTO "Employee" 
                   (emp_id, emp_name, emp_email, role_lvl, sup_id, workload, created_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (emp_id) DO UPDATE SET
                   emp_name = EXCLUDED.emp_name,
                   emp_email = EXCLUDED.emp_email,
                   role_lvl = EXCLUDED.role_lvl,
                   sup_id = EXCLUDED.sup_id,
                   workload = EXCLUDED.workload''',
                (emp[0], emp[1], emp[2], emp[3], emp[4], emp[5], datetime.now())
            )
        
        # Create authentication credentials
        print("Creating auth credentials...")
        auth_data = [
            (1000, 'password1000'),
            (1001, 'password1001'),
            (1002, 'password1002'),
            (1003, 'password1003'),
            (1004, 'password1004'),
            (1005, 'password1005'),
            (1006, 'password1006'),
        ]

        
        for auth in auth_data:
            cursor.execute(
                '''INSERT INTO "Auth" 
                   (emp_id, password) 
                   VALUES (%s, %s)
                   ''',
                auth
            )
        
        # Create approval requests
        print("Creating approval requests...")
        
        # Create some first-level approvals
        level1_approvals = [
            ('TEST-INV-001', 1003, 'Office Supplies'),
            ('TEST-INV-002', 1003, 'Travel'),
            ('TEST-INV-003', 1004, 'Equipment'),
            ('TEST-INV-004', 1005, 'Services'),
            ('TEST-INV-005', 1006, 'Marketing'),
        ]
        
        for invoice_id, emp_id, category in level1_approvals:
            approval_id = str(uuid.uuid4())
            cursor.execute(
                '''INSERT INTO "Approval" 
                   (approval_id, invoice_id, emp_id, created_at, approval_level, category) 
                   VALUES (%s, %s, %s, %s, %s, %s)''',
                (approval_id, invoice_id, emp_id, datetime.now() - timedelta(days=2), 1, category)
            )
        
        # Create some second-level approvals (already approved at level 1)
        level2_approvals = [
            ('TEST-INV-006', 1001, 'Office Supplies'),
            ('TEST-INV-007', 1001, 'Travel'),
            ('TEST-INV-008', 1002, 'Equipment'),
        ]
        
        for invoice_id, emp_id, category in level2_approvals:
            approval_id = str(uuid.uuid4())
            cursor.execute(
                '''INSERT INTO "Approval" 
                   (approval_id, invoice_id, emp_id, created_at, approval_level, category) 
                   VALUES (%s, %s, %s, %s, %s, %s)''',
                (approval_id, invoice_id, emp_id, datetime.now() - timedelta(days=1), 2, category)
            )
        
        # Create some already approved invoices
        approved_invoices = [
            ('TEST-INV-009', 1003, 'Office Supplies', 1),
        ]
        
        for invoice_id, emp_id, category, level in approved_invoices:
            approval_id = str(uuid.uuid4())
            cursor.execute(
                '''INSERT INTO "Approval" 
                   (approval_id, invoice_id, emp_id, created_at, approved_at, approval_level, category) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (approval_id, invoice_id, emp_id, 
                 datetime.now() - timedelta(days=3), 
                 datetime.now() - timedelta(days=2), 
                 level, category)
            )
        
        # Commit all changes
        conn.commit()
        print("Test data successfully created!")
        
        # Print login instructions
        print("\n===== TEST CREDENTIALS =====")
        print("Level 1 Approvers:")
        print("- Employee ID: 1003, Password: password1003 (Carol)")
        print("- Employee ID: 1004, Password: password1004 (Dave)")
        print("- Employee ID: 1005, Password: password1005 (Eve)")
        print("- Employee ID: 1006, Password: password1006 (Frank)")
        print("\nLevel 2 Approvers:")
        print("- Employee ID: 1001, Password: password1001 (Alice)")
        print("- Employee ID: 1002, Password: password1002 (Bob)")
        print("\nManager:")
        print("- Employee ID: 1000, Password: password1000 (John)")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error populating test data: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    populate_test_data()
