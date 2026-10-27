# Resource Allocation System

## Project Description
A web-based **Resource Allocation System** built with **Flask** and **SQLite**. It allows an organization or college to manage shared resources like Computer Labs, Projectors, Laptops, Seminar Halls, and Classrooms. Users can request resources, check availability, and track request status. Admins can approve or reject requests.

---

## Features
- 📊 Dashboard with real-time statistics
- 📦 Resource management with categories and statuses
- 🔍 Search and filter resources by name, category, location, status
- 📝 Submit resource requests with a form
- ✅ Availability checking (prevents double booking / overlapping allocations)
- 📋 Track request status (Pending, Approved, Rejected, Completed)
- ⚙️ Admin panel to manage resources and approve/reject requests
- 📅 Allocation history with filters
- 📈 Reports with statistics and visual bars

---

## Technologies Used
| Technology | Purpose              |
|------------|----------------------|
| Python 3.13 | Backend language    |
| Flask       | Web framework       |
| SQLite      | Database            |
| HTML        | Page structure      |
| CSS         | Styling             |
| JavaScript  | Interactivity       |

---

## Project Structure
```
Resource-Allocation-System/
│
├── app.py              ← Main Flask application
├── init_db.py          ← Database initialization with sample data
├── database.db         ← SQLite database (created by init_db.py)
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
├── .gitignore
│
├── templates/          ← HTML pages
│   ├── base.html           ← Common navbar, alerts, footer
│   ├── index.html          ← Dashboard
│   ├── resources.html      ← Resource listing with search/filter
│   ├── resource_details.html ← Single resource details
│   ├── request.html        ← Request form
│   ├── my_requests.html    ← View all requests
│   ├── allocations.html    ← Allocation history
│   ├── admin.html          ← Admin panel
│   ├── add_resource.html   ← Admin: Add resource
│   ├── edit_resource.html  ← Admin: Edit resource
│   └── reports.html        ← Reports page
│
└── static/             ← CSS and JavaScript
    ├── style.css
    └── script.js
```

---

## Installation Steps

### Step 1: Install Python 3.13
Make sure Python 3.13 is installed. Verify with:
```
python --version
```

### Step 2: Clone or Download the Project
Place the project folder on your computer.

### Step 3: Install Dependencies
Open a terminal inside the project folder and run:
```
python -m pip install -r requirements.txt
```
This installs **Flask**. (SQLite is already built into Python — no separate install needed.)

---

## How to Create the Database

Run the database initialization script once:
```
python init_db.py
```
This creates `database.db` with all tables and sample data.

---

## How to Run the Application

After the database is created, start the Flask server:
```
python app.py
```
Then open your browser and go to:
```
http://127.0.0.1:5000
```

---

## Main Pages

| URL                          | Page               |
|------------------------------|--------------------|
| `/`                          | Dashboard          |
| `/resources`                 | All Resources      |
| `/resource/<id>`             | Resource Details   |
| `/request`                   | Request Form       |
| `/my-requests`               | My Requests        |
| `/allocations`               | Allocation History |
| `/admin`                     | Admin Panel        |
| `/admin/add-resource`        | Add Resource       |
| `/admin/edit-resource/<id>`  | Edit Resource      |
| `/reports`                   | Reports            |

---

## How Availability Checking Works

The core feature of this system is **preventing double-booking** of a resource.

### The Logic:
Two time periods **overlap** if one starts before the other ends AND the other starts before the first ends.

In SQL terms:
```sql
SELECT id FROM allocations
WHERE resource_id = ?
  AND date = ?
  AND status != 'Cancelled'
  AND start_time < <new_end_time>
  AND end_time   > <new_start_time>
```

### Example:
- **Existing allocation**: Projector 1, 10:00 AM – 12:00 PM
- **New request A**: 11:00 AM – 1:00 PM → **CONFLICT** (starts before 12:00)
- **New request B**: 12:00 PM – 2:00 PM → **NO CONFLICT** (starts exactly when old one ends)

### When is it checked?
1. **During form submission** → Shows availability using the Check Availability button (JavaScript + API)
2. **During admin approval** → Server-side double-check before creating the allocation record

---

## Database Tables

### `resources`
| Column      | Type    | Description                  |
|-------------|---------|------------------------------|
| id          | INTEGER | Primary key, auto-increment  |
| name        | TEXT    | Resource name                |
| category    | TEXT    | Type (Computer Lab, etc.)    |
| location    | TEXT    | Where the resource is        |
| capacity    | INTEGER | How many people it fits      |
| description | TEXT    | Extra details                |
| status      | TEXT    | Available / Allocated / Maintenance |

### `requests`
| Column         | Type    | Description               |
|----------------|---------|---------------------------|
| id             | INTEGER | Primary key               |
| requester_name | TEXT    | Who is requesting         |
| email          | TEXT    | Contact email             |
| resource_id    | INTEGER | Foreign key → resources   |
| date           | TEXT    | Requested date (YYYY-MM-DD) |
| start_time     | TEXT    | Start time (HH:MM)        |
| end_time       | TEXT    | End time (HH:MM)          |
| purpose        | TEXT    | Why the resource is needed |
| status         | TEXT    | Pending/Approved/Rejected/Completed |
| created_at     | TEXT    | When the request was made |

### `allocations`
| Column         | Type    | Description               |
|----------------|---------|---------------------------|
| id             | INTEGER | Primary key               |
| request_id     | INTEGER | Foreign key → requests    |
| resource_id    | INTEGER | Foreign key → resources   |
| requester_name | TEXT    | Who it's allocated to     |
| date           | TEXT    | Allocation date           |
| start_time     | TEXT    | Start time                |
| end_time       | TEXT    | End time                  |
| purpose        | TEXT    | Purpose of allocation     |
| status         | TEXT    | Active / Completed / Cancelled |

---

## License
This is a college mini project for educational purposes.
