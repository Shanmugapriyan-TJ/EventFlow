# Event Scheduling & Resource Allocation System

A complete Flask web application for managing events and allocating resources with conflict detection.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)
![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey.svg)

## 📋 Features

### Events Management
- ✅ Add, edit, and delete events
- ✅ Set event title, description, start/end times
- ✅ View all events with duration and allocated resources

### Resources Management
- ✅ Add, edit, and delete resources
- ✅ Three resource types: Room, Instructor, Equipment
- ✅ Track booking count per resource

### Resource Allocation
- ✅ Allocate multiple resources to events
- ✅ Real-time conflict detection
- ✅ Remove allocations easily

### Conflict Detection (Critical)
- ✅ Detects double-booking of resources
- ✅ Handles all overlap cases:
  - Exact overlap
  - Partial overlap
  - Nested intervals
- ✅ Rejects zero-duration events
- ✅ Allows touching times (end == next start)
- ✅ Clear error messages in UI

### Reporting
- ✅ Conflict view page
- ✅ Resource utilization report with date range
- ✅ Shows total hours utilized
- ✅ Lists upcoming bookings

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python Flask 3.0 |
| Database | SQLite with SQLAlchemy ORM |
| Frontend | HTML5 + Bootstrap 5.3 |
| Icons | Bootstrap Icons |
| Styling | Custom CSS with gradients |

## 📁 Project Structure

```
event_scheduler/
├── app.py              # Main Flask application
├── models.py           # SQLAlchemy database models
├── db.sqlite3          # SQLite database (auto-created)
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── templates/
│   ├── base.html       # Base template with navigation
│   ├── events.html     # Events list page
│   ├── add_event.html  # Add event form
│   ├── edit_event.html # Edit event form
│   ├── resources.html  # Resources list page
│   ├── add_resource.html # Add/edit resource form
│   ├── allocate.html   # Resource allocation page
│   ├── conflicts.html  # Conflicts view
│   └── report.html     # Utilization report
└── static/
    └── style.css       # Custom styles
```

## 🚀 How to Run Locally

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Navigate to project directory**
   ```bash
   cd event_scheduler
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

## 🧪 Sample Test Steps

### Test 1: Create Resources
1. Go to Resources → Add Resource
2. Create: "Conference Room A" (type: Room)
3. Create: "John Smith" (type: Instructor)
4. Create: "Projector #1" (type: Equipment)

### Test 2: Create Events
1. Go to Events → Add Event
2. Create "Morning Workshop" (9:00 AM - 12:00 PM)
3. Create "Afternoon Session" (1:00 PM - 3:00 PM)

### Test 3: Allocate Resources
1. Go to Allocate
2. Select "Morning Workshop"
3. Check "Conference Room A" and "John Smith"
4. Click Allocate → Should succeed

### Test 4: Test Conflict Detection
1. Go to Allocate
2. Select "Afternoon Session"
3. Try to allocate "Conference Room A" at overlapping time
4. Should show conflict error

### Test 5: View Report
1. Go to Report
2. Select date range covering your events
3. View utilization hours and upcoming bookings

## 📸 Screenshots

*Add screenshots here after running the application*

| Dashboard | Events List |
|-----------|-------------|
| ![Dashboard](screenshots/dashboard.png) | ![Events](screenshots/events.png) |

| Allocation | Conflicts |
|------------|-----------|
| ![Allocate](screenshots/allocate.png) | ![Conflicts](screenshots/conflicts.png) |

## 🎥 Demo Video

[Watch Demo Video](https://your-demo-link.com)

*Replace with actual demo video link*

## 📝 Database Schema

```
Events (1) ←→ (M) EventResourceAllocation (M) ←→ (1) Resources

Event
├── id (PK)
├── title
├── start_time
├── end_time
└── description

Resource
├── id (PK)
├── name
└── type (room/instructor/equipment)

EventResourceAllocation
├── id (PK)
├── event_id (FK)
└── resource_id (FK)
```

## 🔧 API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Dashboard |
| `/events` | GET | List events |
| `/events/add` | GET/POST | Add event |
| `/events/edit/<id>` | GET/POST | Edit event |
| `/resources` | GET | List resources |
| `/resources/add` | GET/POST | Add resource |
| `/allocate` | GET/POST | Allocate resources |
| `/conflicts` | GET | View conflicts |
| `/report` | GET/POST | Utilization report |

## 📄 License

MIT License - Feel free to use for any purpose.


output screenshots : 

<img width="1912" height="1024" alt="image" src="https://github.com/user-attachments/assets/ce66575e-cfdd-40f8-bd6d-f5beb4a00b9a" />
<img width="1906" height="903" alt="image" src="https://github.com/user-attachments/assets/b0583ea0-a25f-434b-9469-c2aac64be074" />
<img width="1915" height="1018" alt="image" src="https://github.com/user-attachments/assets/4beb0d7b-6593-44d2-999b-02a7d1e3f5d7" />
<img width="1919" height="1012" alt="image" src="https://github.com/user-attachments/assets/611b4072-7c7f-4b31-88c4-f0547f655b36" />
<img width="1916" height="1008" alt="image" src="https://github.com/user-attachments/assets/1ad73afb-64af-4366-8ff4-845d4a3e8f82" />
<img width="1917" height="1016" alt="image" src="https://github.com/user-attachments/assets/082dc09b-1329-433c-8e62-3205dbb6baf0" />
<img width="1919" height="1014" alt="image" src="https://github.com/user-attachments/assets/2895bc3f-8a4e-4d84-8f9b-de421a78796f" />
<img width="1917" height="1019" alt="image" src="https://github.com/user-attachments/assets/5abb0266-58cc-4147-b5ae-512e1422af9b" />









