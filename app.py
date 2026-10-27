# app.py - Main Flask Application for Resource Allocation System

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'resource_allocation_secret_key'

# Path to the SQLite database file
DATABASE = 'database.db'


# -------------------------------------------------------
# DATABASE HELPER FUNCTION
# -------------------------------------------------------
def get_db():
    """Connect to the SQLite database and return the connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn


# -------------------------------------------------------
# AVAILABILITY CHECKING FUNCTION
# -------------------------------------------------------
def is_resource_available(resource_id, date, start_time, end_time, exclude_allocation_id=None):
    """
    Check if a resource is available for the given date and time range.

    Overlap logic:
    - Existing:  [A --------- B]
    - New:            [C --------- D]
    - Overlap if: C < B AND D > A
    - No overlap if: D <= A OR C >= B
    - Example: existing 10:00-12:00, new 12:00-14:00 => D(14:00) > A(10:00) but C(12:00) >= B(12:00) => NO overlap
    """
    conn = get_db()
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

    cursor = conn.execute(query, params)
    conflict = cursor.fetchone()
    conn.close()
    return conflict is None  # True = available, False = conflict exists


# -------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------
@app.route('/')
def dashboard():
    """Main dashboard showing summary statistics and recent requests."""
    conn = get_db()

    # Resource statistics
    total_resources = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    available_resources = conn.execute("SELECT COUNT(*) FROM resources WHERE status='Available'").fetchone()[0]
    allocated_resources = conn.execute("SELECT COUNT(*) FROM resources WHERE status='Allocated'").fetchone()[0]
    maintenance_resources = conn.execute("SELECT COUNT(*) FROM resources WHERE status='Maintenance'").fetchone()[0]

    # Request statistics
    pending_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status='Pending'").fetchone()[0]
    approved_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status='Approved'").fetchone()[0]
    rejected_requests = conn.execute("SELECT COUNT(*) FROM requests WHERE status='Rejected'").fetchone()[0]
    total_requests = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]

    # Recent requests (last 5)
    recent_requests = conn.execute("""
        SELECT r.id, r.requester_name, r.purpose, r.date, r.start_time, r.end_time,
               r.status, res.name as resource_name
        FROM requests r
        JOIN resources res ON r.resource_id = res.id
        ORDER BY r.created_at DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    stats = {
        'total_resources': total_resources,
        'available_resources': available_resources,
        'allocated_resources': allocated_resources,
        'maintenance_resources': maintenance_resources,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'total_requests': total_requests
    }

    return render_template('index.html', stats=stats, recent_requests=recent_requests)


# -------------------------------------------------------
# RESOURCES - LIST PAGE
# -------------------------------------------------------
@app.route('/resources')
def resources():
    """Show all resources with search and filter support."""
    conn = get_db()

    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    location = request.args.get('location', '').strip()

    query = "SELECT * FROM resources WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR category LIKE ? OR location LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    if category:
        query += " AND category = ?"
        params.append(category)
    if status:
        query += " AND status = ?"
        params.append(status)
    if location:
        query += " AND location LIKE ?"
        params.append(f'%{location}%')

    query += " ORDER BY name"
    all_resources = conn.execute(query, params).fetchall()

    # For filter dropdowns
    categories = conn.execute("SELECT DISTINCT category FROM resources ORDER BY category").fetchall()
    locations = conn.execute("SELECT DISTINCT location FROM resources ORDER BY location").fetchall()

    conn.close()

    return render_template('resources.html',
                           resources=all_resources,
                           categories=categories,
                           locations=locations,
                           search=search,
                           selected_category=category,
                           selected_status=status,
                           selected_location=location)


# -------------------------------------------------------
# RESOURCE DETAILS
# -------------------------------------------------------
@app.route('/resource/<int:resource_id>')
def resource_details(resource_id):
    """Show details of a specific resource and its recent allocations."""
    conn = get_db()
    resource = conn.execute("SELECT * FROM resources WHERE id = ?", (resource_id,)).fetchone()

    if not resource:
        flash('Resource not found.', 'error')
        return redirect(url_for('resources'))

    # Recent allocations for this resource
    allocations = conn.execute("""
        SELECT a.*, req.requester_name
        FROM allocations a
        JOIN requests req ON a.request_id = req.id
        WHERE a.resource_id = ?
        ORDER BY a.date DESC, a.start_time DESC
        LIMIT 10
    """, (resource_id,)).fetchall()

    conn.close()
    return render_template('resource_details.html', resource=resource, allocations=allocations)


# -------------------------------------------------------
# REQUEST RESOURCE - FORM
# -------------------------------------------------------
@app.route('/request', methods=['GET', 'POST'])
def request_resource():
    """Handle resource request form."""
    conn = get_db()

    if request.method == 'POST':
        requester_name = request.form.get('requester_name', '').strip()
        email = request.form.get('email', '').strip()
        resource_id = request.form.get('resource_id', '').strip()
        date = request.form.get('date', '').strip()
        start_time = request.form.get('start_time', '').strip()
        end_time = request.form.get('end_time', '').strip()
        purpose = request.form.get('purpose', '').strip()

        # --- Validation ---
        errors = []
        if not requester_name:
            errors.append("Requester name is required.")
        if not email:
            errors.append("Email is required.")
        if not resource_id:
            errors.append("Please select a resource.")
        if not date:
            errors.append("Date is required.")
        if not start_time:
            errors.append("Start time is required.")
        if not end_time:
            errors.append("End time is required.")
        if not purpose:
            errors.append("Purpose is required.")

        if start_time and end_time and end_time <= start_time:
            errors.append("End time must be after start time.")

        if errors:
            all_resources = conn.execute(
                "SELECT * FROM resources WHERE status != 'Maintenance' ORDER BY name"
            ).fetchall()
            conn.close()
            return render_template('request.html',
                                   resources=all_resources,
                                   errors=errors,
                                   form_data=request.form)

        # --- Save to DB ---
        try:
            conn.execute("""
                INSERT INTO requests (requester_name, email, resource_id, date, start_time, end_time, purpose, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
            """, (requester_name, email, resource_id, date, start_time, end_time, purpose,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            flash('Your request has been submitted successfully! It is pending admin approval.', 'success')
            conn.close()
            return redirect(url_for('my_requests'))
        except Exception as e:
            conn.close()
            flash('An error occurred while submitting your request. Please try again.', 'error')
            return redirect(url_for('request_resource'))

    # GET: Show the form
    all_resources = conn.execute(
        "SELECT * FROM resources WHERE status != 'Maintenance' ORDER BY name"
    ).fetchall()
    # Pre-select resource if passed via URL
    selected_resource_id = request.args.get('resource_id', '')
    conn.close()

    return render_template('request.html',
                           resources=all_resources,
                           selected_resource_id=selected_resource_id,
                           errors=[],
                           form_data={})


# -------------------------------------------------------
# MY REQUESTS PAGE
# -------------------------------------------------------
@app.route('/my-requests')
def my_requests():
    """Show all submitted requests with their status."""
    conn = get_db()
    all_requests = conn.execute("""
        SELECT r.id, r.requester_name, r.email, r.date, r.start_time, r.end_time,
               r.purpose, r.status, r.created_at, res.name as resource_name
        FROM requests r
        JOIN resources res ON r.resource_id = res.id
        ORDER BY r.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('my_requests.html', requests=all_requests)


# -------------------------------------------------------
# ALLOCATIONS PAGE
# -------------------------------------------------------
@app.route('/allocations')
def allocations():
    """Show all approved allocations with optional filters."""
    conn = get_db()

    filter_resource = request.args.get('resource_id', '').strip()
    filter_date = request.args.get('date', '').strip()

    query = """
        SELECT a.id, a.requester_name, a.date, a.start_time, a.end_time,
               a.purpose, a.status, res.name as resource_name
        FROM allocations a
        JOIN resources res ON a.resource_id = res.id
        WHERE 1=1
    """
    params = []

    if filter_resource:
        query += " AND a.resource_id = ?"
        params.append(filter_resource)
    if filter_date:
        query += " AND a.date = ?"
        params.append(filter_date)

    query += " ORDER BY a.date DESC, a.start_time DESC"
    all_allocations = conn.execute(query, params).fetchall()

    all_resources = conn.execute("SELECT id, name FROM resources ORDER BY name").fetchall()
    conn.close()

    return render_template('allocations.html',
                           allocations=all_allocations,
                           all_resources=all_resources,
                           filter_resource=filter_resource,
                           filter_date=filter_date)


# -------------------------------------------------------
# REPORTS PAGE
# -------------------------------------------------------
@app.route('/reports')
def reports():
    """Show system-wide statistics and summary."""
    conn = get_db()

    stats = {
        'total_resources': conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0],
        'available_resources': conn.execute("SELECT COUNT(*) FROM resources WHERE status='Available'").fetchone()[0],
        'allocated_resources': conn.execute("SELECT COUNT(*) FROM resources WHERE status='Allocated'").fetchone()[0],
        'maintenance_resources': conn.execute("SELECT COUNT(*) FROM resources WHERE status='Maintenance'").fetchone()[0],
        'total_requests': conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0],
        'pending_requests': conn.execute("SELECT COUNT(*) FROM requests WHERE status='Pending'").fetchone()[0],
        'approved_requests': conn.execute("SELECT COUNT(*) FROM requests WHERE status='Approved'").fetchone()[0],
        'rejected_requests': conn.execute("SELECT COUNT(*) FROM requests WHERE status='Rejected'").fetchone()[0],
        'completed_requests': conn.execute("SELECT COUNT(*) FROM requests WHERE status='Completed'").fetchone()[0],
    }

    # Resources by category
    by_category = conn.execute("""
        SELECT category, COUNT(*) as count FROM resources GROUP BY category ORDER BY category
    """).fetchall()

    # Requests by month (last 6 months)
    recent_by_month = conn.execute("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM requests
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """).fetchall()

    conn.close()
    return render_template('reports.html', stats=stats, by_category=by_category, recent_by_month=recent_by_month)


# -------------------------------------------------------
# ADMIN PANEL
# -------------------------------------------------------
@app.route('/admin')
def admin():
    """Admin panel showing all resources and requests."""
    conn = get_db()

    all_resources = conn.execute("SELECT * FROM resources ORDER BY name").fetchall()
    all_requests = conn.execute("""
        SELECT r.id, r.requester_name, r.email, r.date, r.start_time, r.end_time,
               r.purpose, r.status, r.created_at, res.name as resource_name, res.id as resource_id
        FROM requests r
        JOIN resources res ON r.resource_id = res.id
        ORDER BY r.created_at DESC
    """).fetchall()

    conn.close()
    return render_template('admin.html', resources=all_resources, requests=all_requests)


# -------------------------------------------------------
# ADMIN - ADD RESOURCE
# -------------------------------------------------------
@app.route('/admin/add-resource', methods=['GET', 'POST'])
def add_resource():
    """Admin: Add a new resource."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        location = request.form.get('location', '').strip()
        capacity = request.form.get('capacity', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Available').strip()

        errors = []
        if not name:
            errors.append("Resource name is required.")
        if not category:
            errors.append("Category is required.")
        if not location:
            errors.append("Location is required.")

        if errors:
            return render_template('add_resource.html', errors=errors, form_data=request.form)

        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO resources (name, category, location, capacity, description, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, category, location, capacity or None, description, status))
            conn.commit()
            flash(f'Resource "{name}" added successfully!', 'success')
        except Exception:
            flash('Error adding resource. Please try again.', 'error')
        finally:
            conn.close()

        return redirect(url_for('admin'))

    return render_template('add_resource.html', errors=[], form_data={})


# -------------------------------------------------------
# ADMIN - EDIT RESOURCE
# -------------------------------------------------------
@app.route('/admin/edit-resource/<int:resource_id>', methods=['GET', 'POST'])
def edit_resource(resource_id):
    """Admin: Edit an existing resource."""
    conn = get_db()
    resource = conn.execute("SELECT * FROM resources WHERE id = ?", (resource_id,)).fetchone()

    if not resource:
        flash('Resource not found.', 'error')
        conn.close()
        return redirect(url_for('admin'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        location = request.form.get('location', '').strip()
        capacity = request.form.get('capacity', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Available').strip()

        errors = []
        if not name:
            errors.append("Resource name is required.")
        if not category:
            errors.append("Category is required.")
        if not location:
            errors.append("Location is required.")

        if errors:
            conn.close()
            return render_template('edit_resource.html', errors=errors, resource=resource)

        try:
            conn.execute("""
                UPDATE resources SET name=?, category=?, location=?, capacity=?, description=?, status=?
                WHERE id=?
            """, (name, category, location, capacity or None, description, status, resource_id))
            conn.commit()
            flash(f'Resource "{name}" updated successfully!', 'success')
        except Exception:
            flash('Error updating resource.', 'error')
        finally:
            conn.close()

        return redirect(url_for('admin'))

    conn.close()
    return render_template('edit_resource.html', resource=resource, errors=[])


# -------------------------------------------------------
# ADMIN - DELETE RESOURCE
# -------------------------------------------------------
@app.route('/admin/delete-resource/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    """Admin: Delete a resource."""
    conn = get_db()
    try:
        resource = conn.execute("SELECT name FROM resources WHERE id=?", (resource_id,)).fetchone()
        if resource:
            conn.execute("DELETE FROM resources WHERE id=?", (resource_id,))
            conn.commit()
            flash(f'Resource "{resource["name"]}" deleted successfully.', 'success')
        else:
            flash('Resource not found.', 'error')
    except Exception:
        flash('Error deleting resource.', 'error')
    finally:
        conn.close()
    return redirect(url_for('admin'))


# -------------------------------------------------------
# ADMIN - APPROVE REQUEST
# -------------------------------------------------------
@app.route('/admin/approve/<int:request_id>', methods=['POST'])
def approve_request(request_id):
    """Admin: Approve a request after checking for conflicts."""
    conn = get_db()

    req = conn.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()

    if not req:
        flash('Request not found.', 'error')
        conn.close()
        return redirect(url_for('admin'))

    if req['status'] != 'Pending':
        flash('Only pending requests can be approved.', 'error')
        conn.close()
        return redirect(url_for('admin'))

    # Double-check availability before approving
    available = is_resource_available(req['resource_id'], req['date'], req['start_time'], req['end_time'])

    if not available:
        flash(
            f'Cannot approve: Resource is already allocated on {req["date"]} '
            f'from {req["start_time"]} to {req["end_time"]}. Please reject this request.',
            'error'
        )
        conn.close()
        return redirect(url_for('admin'))

    try:
        # Approve the request
        conn.execute("UPDATE requests SET status='Approved' WHERE id=?", (request_id,))

        # Create allocation record
        conn.execute("""
            INSERT INTO allocations (request_id, resource_id, requester_name, date, start_time, end_time, purpose, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')
        """, (req['id'], req['resource_id'], req['requester_name'],
              req['date'], req['start_time'], req['end_time'], req['purpose']))

        # Update resource status to Allocated
        conn.execute("UPDATE resources SET status='Allocated' WHERE id=?", (req['resource_id'],))

        conn.commit()
        flash(f'Request #{request_id} approved and allocation created successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error approving request. Please try again.', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin'))


# -------------------------------------------------------
# ADMIN - REJECT REQUEST
# -------------------------------------------------------
@app.route('/admin/reject/<int:request_id>', methods=['POST'])
def reject_request(request_id):
    """Admin: Reject a pending request."""
    conn = get_db()
    req = conn.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()

    if not req:
        flash('Request not found.', 'error')
    elif req['status'] != 'Pending':
        flash('Only pending requests can be rejected.', 'error')
    else:
        try:
            conn.execute("UPDATE requests SET status='Rejected' WHERE id=?", (request_id,))
            conn.commit()
            flash(f'Request #{request_id} has been rejected.', 'success')
        except Exception:
            flash('Error rejecting request.', 'error')

    conn.close()
    return redirect(url_for('admin'))


# -------------------------------------------------------
# API: CHECK AVAILABILITY (AJAX)
# -------------------------------------------------------
@app.route('/api/check-availability')
def check_availability():
    """API endpoint to check resource availability (called via JavaScript)."""
    resource_id = request.args.get('resource_id')
    date = request.args.get('date')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')

    if not all([resource_id, date, start_time, end_time]):
        return jsonify({'error': 'Missing parameters'}), 400

    if end_time <= start_time:
        return jsonify({'available': False, 'message': 'End time must be after start time.'})

    available = is_resource_available(resource_id, date, start_time, end_time)
    if available:
        return jsonify({'available': True, 'message': 'Resource is available for the selected time.'})
    else:
        return jsonify({'available': False, 'message': 'Resource is already allocated during the requested time.'})


# -------------------------------------------------------
# RUN THE APP
# -------------------------------------------------------
if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        print("WARNING: database.db not found. Please run: python init_db.py")
    app.run(debug=True)
