# terminal_app.py - Terminal-based Resource Allocation System
# Developed using standard Python and SQLite for direct console execution.

import sqlite3
import os
from datetime import datetime

# Database file location (shared with the web application)
DATABASE = 'database.db'


# ---------------------------------------------------------------------------
# DATABASE HELPER FUNCTIONS
# ---------------------------------------------------------------------------
def get_db_connection():
    """Connect to SQLite database and configure row access by column name."""
    if not os.path.exists(DATABASE):
        print(f"\n[ERROR] Database file '{DATABASE}' was not found.")
        print("Please ensure database.db exists in this directory.\n")
        return None
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"\n[Database Connection Error]: {e}\n")
        return None


def is_resource_available(resource_id, date, start_time, end_time, exclude_allocation_id=None):
    """
    Check if a resource is available for a specified date and time window.
    An overlap exists if an active allocation satisfies:
      start_time < new_end_time AND end_time > new_start_time
    Returns True if available (no conflict), False if a conflict exists.
    """
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        query = """
            SELECT id FROM allocations
            WHERE resource_id = ?
              AND date = ?
              AND status != 'Cancelled'
              AND start_time < ?
              AND end_time > ?
        """
        params = [resource_id, date, end_time, start_time]

        if exclude_allocation_id:
            query += " AND id != ?"
            params.append(exclude_allocation_id)

        cursor = conn.cursor()
        cursor.execute(query, params)
        conflict = cursor.fetchone()
        return conflict is None
    except sqlite3.Error as e:
        print(f"[Database Error during availability check]: {e}")
        return False
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# INPUT VALIDATION HELPERS
# ---------------------------------------------------------------------------
def validate_date(date_text):
    """Validate date format YYYY-MM-DD."""
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_time(time_text):
    """Validate time format HH:MM."""
    try:
        datetime.strptime(time_text, '%H:%M')
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# 1. VIEW RESOURCES
# ---------------------------------------------------------------------------
def view_resources():
    """Display all resources from the existing database."""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, location, capacity, status FROM resources ORDER BY id")
        rows = cursor.fetchall()

        print("\n" + "=" * 80)
        print("                              RESOURCES LIST")
        print("=" * 80)
        if not rows:
            print("No resources found.")
        else:
            print(f"{'ID':<4} | {'Name':<22} | {'Category':<15} | {'Status':<12} | {'Location':<20}")
            print("-" * 80)
            for r in rows:
                print(f"{r['id']:<4} | {r['name']:<22} | {r['category']:<15} | {r['status']:<12} | {r['location']:<20}")
        print("=" * 80 + "\n")
    except sqlite3.Error as e:
        print(f"\n[Database Error] Could not retrieve resources: {e}\n")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. REQUEST RESOURCE
# ---------------------------------------------------------------------------
def request_resource():
    """Prompt user for details and submit a new resource request."""
    conn = get_db_connection()
    if conn is None:
        return

    print("\n" + "=" * 50)
    print("                REQUEST RESOURCE")
    print("=" * 50)

    try:
        # 1. Requester Name
        name = input("Enter your Name: ").strip()
        if not name:
            print("[Validation Error] Name cannot be empty.\n")
            return

        # 2. Requester Email
        email = input("Enter your Email: ").strip()
        if not email:
            print("[Validation Error] Email cannot be empty.\n")
            return

        # Display available resources list for quick reference
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, status FROM resources ORDER BY id")
        resources = cursor.fetchall()
        print("\nAvailable Resources:")
        for res in resources:
            status_tag = f" ({res['status']})" if res['status'] != 'Available' else ""
            print(f"  [{res['id']}] {res['name']} - {res['category']}{status_tag}")

        # 3. Resource ID or Name
        resource_input = input("\nEnter Resource ID or Name: ").strip()
        if not resource_input:
            print("[Validation Error] Resource cannot be empty.\n")
            return

        # Support both numeric ID and Resource Name input
        if resource_input.isdigit():
            cursor.execute("SELECT id, name, status FROM resources WHERE id = ?", (int(resource_input),))
        else:
            cursor.execute("SELECT id, name, status FROM resources WHERE LOWER(name) = LOWER(?)", (resource_input,))
        
        resource = cursor.fetchone()
        if not resource:
            print(f"[Validation Error] Resource '{resource_input}' does not exist.\n")
            return

        resource_id = resource['id']

        if resource['status'] == 'Maintenance':
            print("\nRESOURCE NOT AVAILABLE")
            print(f"Reason: Resource '{resource['name']}' is currently under Maintenance.\n")
            return

        # 4. Date (YYYY-MM-DD)
        date = input("Enter Date (YYYY-MM-DD): ").strip()
        if not validate_date(date):
            print("[Validation Error] Invalid date format. Please use YYYY-MM-DD (e.g. 2026-10-15).\n")
            return

        # 5. Start Time (HH:MM)
        start_time = input("Enter Start Time (HH:MM, e.g. 09:00): ").strip()
        if not validate_time(start_time):
            print("[Validation Error] Invalid start time format. Please use HH:MM (e.g. 09:00).\n")
            return

        # 6. End Time (HH:MM)
        end_time = input("Enter End Time (HH:MM, e.g. 11:00): ").strip()
        if not validate_time(end_time):
            print("[Validation Error] Invalid end time format. Please use HH:MM (e.g. 11:00).\n")
            return

        if end_time <= start_time:
            print("[Validation Error] End time must be after start time.\n")
            return

        # 7. Purpose
        purpose = input("Enter Purpose: ").strip()
        if not purpose:
            print("[Validation Error] Purpose cannot be empty.\n")
            return

        # Conflict check
        available = is_resource_available(resource_id, date, start_time, end_time)
        if not available:
            print("\n" + "=" * 50)
            print("RESOURCE NOT AVAILABLE")
            print("Reason: Resource is already allocated during this time.")
            print("=" * 50 + "\n")
            return

        # Save request with 'Pending' status
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO requests (requester_name, email, resource_id, date, start_time, end_time, purpose, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
        """, (name, email, resource_id, date, start_time, end_time, purpose, now_str))
        conn.commit()
        request_id = cursor.lastrowid

        print("\n" + "=" * 50)
        print("REQUEST SUBMITTED SUCCESSFULLY!")
        print(f"Request ID : #{request_id}")
        print(f"Resource   : {resource['name']}")
        print(f"Date & Time: {date} ({start_time} - {end_time})")
        print("Status     : Pending")
        print("=" * 50 + "\n")

    except sqlite3.Error as e:
        print(f"\n[Database Error] Could not save request: {e}\n")
    finally:
        conn.close()


# -----------------------------------------------------------
# 3. VIEW MY REQUESTS
# -----------------------------------------------------------
def view_my_requests():
    """Display requests filtered by requester's name or email."""
    conn = get_db_connection()
    if conn is None:
        return

    print("\n" + "=" * 50)
    print("                 MY REQUESTS")
    print("=" * 50)

    identifier = input("Enter your Name or Email: ").strip()
    if not identifier:
        print("[Validation Error] Input cannot be empty.\n")
        conn.close()
        return

    try:
        cursor = conn.cursor()
        search_pattern = f"%{identifier}%"
        query = """
            SELECT r.id, r.requester_name, r.email, r.date, r.start_time, r.end_time,
                   r.purpose, r.status, r.created_at, res.name AS resource_name
            FROM requests r
            JOIN resources res ON r.resource_id = res.id
            WHERE LOWER(r.requester_name) LIKE LOWER(?) OR LOWER(r.email) LIKE LOWER(?)
            ORDER BY r.id DESC
        """
        cursor.execute(query, (search_pattern, search_pattern))
        rows = cursor.fetchall()

        print("\n" + "=" * 90)
        print(f"Requests for: {identifier}")
        print("=" * 90)

        if not rows:
            print(f"No requests found for '{identifier}'.")
        else:
            print(f"{'ID':<4} | {'Resource':<20} | {'Date':<10} | {'Time':<13} | {'Status':<10} | {'Purpose':<22}")
            print("-" * 90)
            for r in rows:
                time_range = f"{r['start_time']}-{r['end_time']}"
                print(f"{r['id']:<4} | {r['resource_name']:<20} | {r['date']:<10} | {time_range:<13} | {r['status']:<10} | {r['purpose']:<22}")

        print("=" * 90 + "\n")
    except sqlite3.Error as e:
        print(f"\n[Database Error] Could not retrieve requests: {e}\n")
    finally:
        conn.close()


# -----------------------------------------------------------
# 4. VIEW ALL REQUESTS (ADMIN)
# -----------------------------------------------------------
def view_all_requests():
    """Display all requests in the system."""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        query = """
            SELECT r.id, r.requester_name, r.email, r.date, r.start_time, r.end_time,
                   r.purpose, r.status, r.created_at, res.name AS resource_name
            FROM requests r
            JOIN resources res ON r.resource_id = res.id
            ORDER BY r.id DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        print("\n" + "=" * 100)
        print("                                  ALL REQUESTS")
        print("=" * 100)

        if not rows:
            print("No requests found.")
        else:
            print(f"{'ID':<4} | {'Requester':<16} | {'Resource':<18} | {'Date':<10} | {'Time':<13} | {'Status':<10} | {'Purpose':<25}")
            print("-" * 100)
            for r in rows:
                time_range = f"{r['start_time']}-{r['end_time']}"
                print(f"{r['id']:<4} | {r['requester_name']:<16} | {r['resource_name']:<18} | {r['date']:<10} | {time_range:<13} | {r['status']:<10} | {r['purpose']:<25}")

        print("=" * 100 + "\n")
    except sqlite3.Error as e:
        print(f"\n[Database Error] Could not retrieve requests: {e}\n")
    finally:
        conn.close()


# -----------------------------------------------------------
# 5. APPROVE REQUEST
# -----------------------------------------------------------
def approve_request():
    """Approve a pending request and create an active allocation."""
    conn = get_db_connection()
    if conn is None:
        return

    print("\n" + "=" * 50)
    print("                APPROVE REQUEST")
    print("=" * 50)

    req_input = input("Enter Request ID to approve: ").strip()
    if not req_input.isdigit():
        print("[Validation Error] Request ID must be a valid number.\n")
        conn.close()
        return

    request_id = int(req_input)

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, res.name AS resource_name
            FROM requests r
            JOIN resources res ON r.resource_id = res.id
            WHERE r.id = ?
        """, (request_id,))
        req = cursor.fetchone()

        if not req:
            print(f"[Error] Request #{request_id} not found.\n")
            return

        if req['status'] != 'Pending':
            print(f"[Notice] Request #{request_id} is already '{req['status']}'. Only Pending requests can be approved.\n")
            return

        # Double-check resource availability before approval
        available = is_resource_available(req['resource_id'], req['date'], req['start_time'], req['end_time'])
        if not available:
            print("\n" + "=" * 50)
            print("RESOURCE NOT AVAILABLE")
            print(f"Reason: Resource is already allocated during this time.")
            print(f"Details: {req['resource_name']} on {req['date']} ({req['start_time']} - {req['end_time']})")
            print("=" * 50 + "\n")
            return

        # 1. Update request status to 'Approved'
        cursor.execute("UPDATE requests SET status = 'Approved' WHERE id = ?", (request_id,))

        # 2. Insert into allocations table
        cursor.execute("""
            INSERT INTO allocations (request_id, resource_id, requester_name, date, start_time, end_time, purpose, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')
        """, (req['id'], req['resource_id'], req['requester_name'], req['date'], req['start_time'], req['end_time'], req['purpose']))

        # 3. Update resource status to 'Allocated'
        cursor.execute("UPDATE resources SET status = 'Allocated' WHERE id = ?", (req['resource_id'],))

        conn.commit()

        print("\n" + "=" * 50)
        print(f"SUCCESS: Request #{request_id} approved!")
        print(f"Resource  : {req['resource_name']}")
        print(f"Requester : {req['requester_name']}")
        print(f"Date & Time: {req['date']} ({req['start_time']} - {req['end_time']})")
        print("Allocation created with status 'Active'.")
        print("=" * 50 + "\n")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n[Database Error] Could not approve request: {e}\n")
    finally:
        conn.close()


# -----------------------------------------------------------
# 6. REJECT REQUEST
# -----------------------------------------------------------
def reject_request():
    """Reject a request by updating its status to Rejected."""
    conn = get_db_connection()
    if conn is None:
        return

    print("\n" + "=" * 50)
    print("                 REJECT REQUEST")
    print("=" * 50)

    req_input = input("Enter Request ID to reject: ").strip()
    if not req_input.isdigit():
        print("[Validation Error] Request ID must be a valid number.\n")
        conn.close()
        return

    request_id = int(req_input)

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, status, requester_name FROM requests WHERE id = ?", (request_id,))
        req = cursor.fetchone()

        if not req:
            print(f"[Error] Request #{request_id} not found.\n")
            return

        if req['status'] != 'Pending':
            print(f"[Notice] Request #{request_id} is already '{req['status']}'. Only Pending requests can be rejected.\n")
            return

        cursor.execute("UPDATE requests SET status = 'Rejected' WHERE id = ?", (request_id,))
        conn.commit()

        print("\n" + "=" * 50)
        print(f"SUCCESS: Request #{request_id} has been Rejected.")
        print(f"Requester: {req['requester_name']}")
        print("=" * 50 + "\n")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n[Database Error] Could not reject request: {e}\n")
    finally:
        conn.close()


# -----------------------------------------------------------
# 7. VIEW ALLOCATIONS
# -----------------------------------------------------------
def view_allocations():
    """Display allocation records with resource and request details."""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        query = """
            SELECT a.id, a.request_id, a.requester_name, a.date, a.start_time, a.end_time,
                   a.purpose, a.status, res.name AS resource_name
            FROM allocations a
            JOIN resources res ON a.resource_id = res.id
            ORDER BY a.date DESC, a.start_time DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        print("\n" + "=" * 100)
        print("                               ALLOCATIONS LIST")
        print("=" * 100)

        if not rows:
            print("No allocations found.")
        else:
            print(f"{'Alloc ID':<8} | {'Req ID':<6} | {'Resource':<18} | {'Date':<10} | {'Time':<13} | {'Status':<10} | {'Requester':<18}")
            print("-" * 100)
            for r in rows:
                time_range = f"{r['start_time']}-{r['end_time']}"
                print(f"{r['id']:<8} | {r['request_id']:<6} | {r['resource_name']:<18} | {r['date']:<10} | {time_range:<13} | {r['status']:<10} | {r['requester_name']:<18}")

        print("=" * 100 + "\n")
    except sqlite3.Error as e:
        print(f"\n[Database Error] Could not retrieve allocations: {e}\n")
    finally:
        conn.close()


# -----------------------------------------------------------
# 8. REPORTS
# -----------------------------------------------------------
def view_reports():
    """Display summary statistics of the system."""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()

        total_resources = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        total_requests = cursor.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        pending_requests = cursor.execute("SELECT COUNT(*) FROM requests WHERE status = 'Pending'").fetchone()[0]
        approved_requests = cursor.execute("SELECT COUNT(*) FROM requests WHERE status = 'Approved'").fetchone()[0]
        rejected_requests = cursor.execute("SELECT COUNT(*) FROM requests WHERE status = 'Rejected'").fetchone()[0]
        total_allocations = cursor.execute("SELECT COUNT(*) FROM allocations").fetchone()[0]

        print("\n" + "=" * 50)
        print("              SYSTEM STATISTICS & REPORTS")
        print("=" * 50)
        print(f"Total resources   : {total_resources}")
        print(f"Total requests    : {total_requests}")
        print(f"Pending requests  : {pending_requests}")
        print(f"Approved requests : {approved_requests}")
        print(f"Rejected requests : {rejected_requests}")
        print(f"Total allocations : {total_allocations}")
        print("=" * 50 + "\n")

    except sqlite3.Error as e:
        print(f"\n[Database Error] Could not generate reports: {e}\n")
    finally:
        conn.close()


# -----------------------------------------------------------
# MAIN MENU LOOP
# -----------------------------------------------------------
def main():
    """Main application loop displaying the console menu."""
    while True:
        print("========================================")
        print("       RESOURCE ALLOCATION SYSTEM")
        print("========================================")
        print()
        print("1. View Resources")
        print("2. Request Resource")
        print("3. View My Requests")
        print("4. View All Requests")
        print("5. Approve Request")
        print("6. Reject Request")
        print("7. View Allocations")
        print("8. Reports")
        print("0. Exit")
        print()

        choice = input("Enter your choice (0-8): ").strip().lower()

        if choice == '1':
            view_resources()
        elif choice == '2':
            request_resource()
        elif choice == '3':
            view_my_requests()
        elif choice == '4':
            view_all_requests()
        elif choice == '5':
            approve_request()
        elif choice == '6':
            reject_request()
        elif choice == '7':
            view_allocations()
        elif choice == '8':
            view_reports()
        elif choice in ('0', '9', 'exit', 'q'):
            print("\nThank you for using Resource Allocation System!\n")
            break
        else:
            print("\n[Invalid Choice] Please enter a valid number (0-8).\n")


if __name__ == '__main__':
    main()
