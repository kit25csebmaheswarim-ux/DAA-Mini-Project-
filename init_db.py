# init_db.py - Initialize the SQLite database with tables and sample data

import sqlite3
import os
from datetime import datetime, timedelta

DATABASE = 'database.db'


def init_db():
    """Create all tables and insert sample data."""
    # Remove old database if exists (fresh start)
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
        print(f"Removed old {DATABASE}")

    conn = sqlite3.connect(DATABASE)

    # ----------------------------
    # CREATE TABLES
    # ----------------------------
    conn.executescript("""
        -- Resources table
        CREATE TABLE IF NOT EXISTS resources (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            location    TEXT NOT NULL,
            capacity    INTEGER,
            description TEXT,
            status      TEXT NOT NULL DEFAULT 'Available'
        );

        -- Requests table
        CREATE TABLE IF NOT EXISTS requests (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_name TEXT NOT NULL,
            email          TEXT NOT NULL,
            resource_id    INTEGER NOT NULL,
            date           TEXT NOT NULL,
            start_time     TEXT NOT NULL,
            end_time       TEXT NOT NULL,
            purpose        TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'Pending',
            created_at     TEXT NOT NULL,
            FOREIGN KEY (resource_id) REFERENCES resources(id)
        );

        -- Allocations table
        CREATE TABLE IF NOT EXISTS allocations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id     INTEGER NOT NULL,
            resource_id    INTEGER NOT NULL,
            requester_name TEXT NOT NULL,
            date           TEXT NOT NULL,
            start_time     TEXT NOT NULL,
            end_time       TEXT NOT NULL,
            purpose        TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY (request_id) REFERENCES requests(id),
            FOREIGN KEY (resource_id) REFERENCES resources(id)
        );
    """)

    # ----------------------------
    # INSERT SAMPLE RESOURCES
    # ----------------------------
    resources = [
        ("Computer Lab 1",  "Computer Lab",  "Block A, Ground Floor", 30, "Equipped with 30 PCs and projector. Suitable for programming labs.", "Available"),
        ("Computer Lab 2",  "Computer Lab",  "Block A, First Floor",  25, "25 PCs with dual-monitor setup. Used for data science sessions.", "Allocated"),
        ("Projector 1",     "Projector",     "Block B, Room 201",     None, "Epson EB-X41 projector with HDMI and VGA support.", "Available"),
        ("Projector 2",     "Projector",     "Block C, Seminar Hall", None, "BenQ MH550 Full HD projector. Available for seminars.", "Available"),
        ("Laptop 1",        "Laptop",        "Admin Office",          None, "Dell Inspiron 15, Core i5, 8GB RAM, 256GB SSD.", "Available"),
        ("Laptop 2",        "Laptop",        "Admin Office",          None, "HP Pavilion, Core i7, 16GB RAM, 512GB SSD.", "Maintenance"),
        ("Seminar Hall",    "Seminar Hall",  "Block D, Ground Floor", 150, "Air-conditioned hall with stage, mic system and projector.", "Available"),
        ("Classroom 101",   "Classroom",     "Block A, Ground Floor", 60,  "Standard classroom with whiteboard and basic projector.", "Available"),
    ]

    conn.executemany("""
        INSERT INTO resources (name, category, location, capacity, description, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, resources)

    # ----------------------------
    # INSERT SAMPLE REQUESTS & ALLOCATIONS
    # ----------------------------
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Sample requests
    requests_data = [
        # (requester_name, email, resource_id, date, start_time, end_time, purpose, status, created_at)
        ("Alice Johnson",  "alice@college.edu",   2, yesterday, "09:00", "11:00", "Python Programming Lab",       "Approved",  now_str),
        ("Bob Smith",      "bob@college.edu",     3, today,     "10:00", "12:00", "Faculty Presentation",         "Approved",  now_str),
        ("Carol White",    "carol@college.edu",   7, tomorrow,  "14:00", "17:00", "Annual Tech Seminar",          "Pending",   now_str),
        ("David Lee",      "david@college.edu",   1, tomorrow,  "09:00", "11:00", "Database Management Lab",      "Pending",   now_str),
        ("Eva Brown",      "eva@college.edu",     4, today,     "13:00", "15:00", "Department Head Meeting",      "Rejected",  now_str),
        ("Frank Wilson",   "frank@college.edu",   8, today,     "08:00", "10:00", "Morning Lecture - CS101",      "Approved",  now_str),
    ]

    conn.executemany("""
        INSERT INTO requests (requester_name, email, resource_id, date, start_time, end_time, purpose, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, requests_data)

    # Create allocations for approved requests
    # Request IDs will be 1, 2, 6 (1-indexed) for approved ones
    allocations_data = [
        # (request_id, resource_id, requester_name, date, start_time, end_time, purpose, status)
        (1, 2, "Alice Johnson",  yesterday, "09:00", "11:00", "Python Programming Lab",  "Completed"),
        (2, 3, "Bob Smith",      today,     "10:00", "12:00", "Faculty Presentation",    "Active"),
        (6, 8, "Frank Wilson",   today,     "08:00", "10:00", "Morning Lecture - CS101", "Active"),
    ]

    conn.executemany("""
        INSERT INTO allocations (request_id, resource_id, requester_name, date, start_time, end_time, purpose, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, allocations_data)

    conn.commit()
    conn.close()

    print("=" * 50)
    print("Database initialized successfully!")
    print(f"File: {DATABASE}")
    print("-" * 50)
    print(f"  Resources inserted : {len(resources)}")
    print(f"  Requests inserted  : {len(requests_data)}")
    print(f"  Allocations created: {len(allocations_data)}")
    print("=" * 50)
    print("Now run:  python app.py")
    print("Open:     http://127.0.0.1:5000")


if __name__ == '__main__':
    init_db()
