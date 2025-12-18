"""
app.py - Main Flask Application for Event Scheduling & Resource Allocation System

This is the main application file containing:
- Flask app configuration
- All route handlers
- Helper functions for conflict detection
- Database initialization

Routes:
    - / : Home page with dashboard
    - /events : List all events
    - /events/add : Add new event
    - /events/edit/<id> : Edit existing event
    - /events/delete/<id> : Delete existing event
    - /resources : List all resources
    - /resources/add : Add new resource
    - /resources/edit/<id> : Edit existing resource
    - /resources/delete/<id> : Delete existing resource
    - /allocate : Allocate resources to events
    - /deallocate/<id> : Remove resource allocation
    - /conflicts : View all current conflicts
    - /report : Resource utilization report
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Event, Resource, EventResourceAllocation
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

# ============================================
# Flask App Configuration
# ============================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with app
db.init_app(app)


# ============================================
# Helper Functions for Conflict Detection
# ============================================

def times_overlap(start1, end1, start2, end2):
    """
    Check if two time windows overlap.
    
    Rules:
    - Returns True if there is any overlap (exact, partial, or nested)
    - End time touching next start time is ALLOWED (not a conflict)
    - start_time == end_time is invalid (handled separately)
    
    Args:
        start1, end1: First time window
        start2, end2: Second time window
    
    Returns:
        bool: True if windows overlap, False otherwise
    """
    # Two intervals overlap if one starts before the other ends
    # Using < instead of <= allows touching times (end1 == start2)
    return start1 < end2 and start2 < end1


def check_resource_conflict(resource_id, start_time, end_time, exclude_event_id=None):
    """
    Check if a resource has any conflicting bookings in the given time window.
    
    This function checks all existing allocations for the resource and returns
    any events that would conflict with the proposed time window.
    
    Args:
        resource_id: ID of the resource to check
        start_time: Proposed start time
        end_time: Proposed end time
        exclude_event_id: Optional event ID to exclude from conflict check
                         (used when editing an existing event)
    
    Returns:
        list: List of conflicting Event objects
    """
    conflicts = []
    
    # Get all allocations for this resource
    allocations = EventResourceAllocation.query.filter_by(resource_id=resource_id).all()
    
    for allocation in allocations:
        # Skip if this is the event we're editing
        if exclude_event_id and allocation.event_id == exclude_event_id:
            continue
        
        event = allocation.event
        
        # Check if times overlap
        if times_overlap(start_time, end_time, event.start_time, event.end_time):
            conflicts.append(event)
    
    return conflicts


def validate_event_times(start_time, end_time):
    """
    Validate event time constraints.
    
    Args:
        start_time: Event start datetime
        end_time: Event end datetime
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if start_time >= end_time:
        return False, "End time must be after start time. Events with zero duration are not allowed."
    
    return True, None


def get_all_conflicts():
    """
    Get all current resource conflicts in the system.
    
    This function finds all cases where a resource is double-booked
    (allocated to multiple events with overlapping times).
    
    Returns:
        list: List of conflict dictionaries with resource and event info
    """
    conflicts = []
    resources = Resource.query.all()
    
    for resource in resources:
        # Get all allocations for this resource
        allocations = EventResourceAllocation.query.filter_by(resource_id=resource.id).all()
        events = [a.event for a in allocations]
        
        # Check each pair of events for conflicts
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                event1 = events[i]
                event2 = events[j]
                
                if times_overlap(event1.start_time, event1.end_time, 
                               event2.start_time, event2.end_time):
                    conflicts.append({
                        'resource': resource,
                        'event1': event1,
                        'event2': event2
                    })
    
    return conflicts


def get_resource_utilization(resource, start_date, end_date):
    """
    Calculate resource utilization within a date range.
    
    Args:
        resource: Resource object
        start_date: Start of date range
        end_date: End of date range
    
    Returns:
        dict: Utilization data including hours and upcoming bookings
    """
    # Get all allocations for this resource
    allocations = EventResourceAllocation.query.filter_by(resource_id=resource.id).all()
    
    total_hours = 0
    upcoming_bookings = []
    now = datetime.now()
    
    for allocation in allocations:
        event = allocation.event
        
        # Calculate overlap with date range for utilization
        event_start = max(event.start_time, start_date)
        event_end = min(event.end_time, end_date)
        
        if event_start < event_end:  # There is overlap with date range
            hours = (event_end - event_start).total_seconds() / 3600
            total_hours += hours
        
        # Track upcoming bookings (future events)
        if event.start_time > now:
            upcoming_bookings.append(event)
    
    # Sort upcoming bookings by start time
    upcoming_bookings.sort(key=lambda e: e.start_time)
    
    return {
        'resource': resource,
        'total_hours': round(total_hours, 2),
        'upcoming_bookings': upcoming_bookings
    }


# ============================================
# Route Handlers
# ============================================

@app.route('/')
def index():
    """
    Home page / Dashboard
    
    Displays summary statistics:
    - Total events count
    - Total resources count
    - Current conflict count
    """
    events_count = Event.query.count()
    resources_count = Resource.query.count()
    conflicts_count = len(get_all_conflicts())
    
    # Get recent events
    recent_events = Event.query.order_by(Event.start_time.desc()).limit(5).all()
    
    return render_template('base.html', 
                          events_count=events_count,
                          resources_count=resources_count,
                          conflicts_count=conflicts_count,
                          recent_events=recent_events,
                          is_home=True)


# ============================================
# Event Routes
# ============================================

@app.route('/events')
def events():
    """List all events with their allocated resources."""
    all_events = Event.query.order_by(Event.start_time).all()
    return render_template('events.html', events=all_events)


@app.route('/events/add', methods=['GET', 'POST'])
def add_event():
    """Add a new event."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        start_time_str = request.form.get('start_time', '')
        end_time_str = request.form.get('end_time', '')
        
        # Validate required fields
        if not title or not start_time_str or not end_time_str:
            flash('Please fill in all required fields.', 'danger')
            return render_template('add_event.html')
        
        try:
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return render_template('add_event.html')
        
        # Validate times
        is_valid, error_msg = validate_event_times(start_time, end_time)
        if not is_valid:
            flash(error_msg, 'danger')
            return render_template('add_event.html')
        
        # Create new event
        event = Event(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(event)
        db.session.commit()
        
        flash(f'Event "{title}" created successfully!', 'success')
        return redirect(url_for('events'))
    
    return render_template('add_event.html')


@app.route('/events/edit/<int:id>', methods=['GET', 'POST'])
def edit_event(id):
    """Edit an existing event with conflict checking."""
    event = Event.query.get_or_404(id)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        start_time_str = request.form.get('start_time', '')
        end_time_str = request.form.get('end_time', '')
        
        # Validate required fields
        if not title or not start_time_str or not end_time_str:
            flash('Please fill in all required fields.', 'danger')
            return render_template('edit_event.html', event=event)
        
        try:
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return render_template('edit_event.html', event=event)
        
        # Validate times
        is_valid, error_msg = validate_event_times(start_time, end_time)
        if not is_valid:
            flash(error_msg, 'danger')
            return render_template('edit_event.html', event=event)
        
        # Check for conflicts with existing allocations
        # If time is being changed, check if any allocated resources would conflict
        if start_time != event.start_time or end_time != event.end_time:
            conflict_resources = []
            for allocation in event.allocations:
                conflicts = check_resource_conflict(
                    allocation.resource_id, 
                    start_time, 
                    end_time, 
                    exclude_event_id=event.id
                )
                if conflicts:
                    conflict_resources.append({
                        'resource': allocation.resource,
                        'conflicting_events': conflicts
                    })
            
            if conflict_resources:
                error_msg = "Cannot update event times. The following resource conflicts would occur:<br>"
                for cr in conflict_resources:
                    event_names = ', '.join([e.title for e in cr['conflicting_events']])
                    error_msg += f"<strong>{cr['resource'].name}</strong> conflicts with: {event_names}<br>"
                flash(error_msg, 'danger')
                return render_template('edit_event.html', event=event)
        
        # Update event
        event.title = title
        event.description = description
        event.start_time = start_time
        event.end_time = end_time
        db.session.commit()
        
        flash(f'Event "{title}" updated successfully!', 'success')
        return redirect(url_for('events'))
    
    return render_template('edit_event.html', event=event)


@app.route('/events/delete/<int:id>', methods=['POST'])
def delete_event(id):
    """Delete an event and its allocations."""
    event = Event.query.get_or_404(id)
    title = event.title
    
    db.session.delete(event)
    db.session.commit()
    
    flash(f'Event "{title}" deleted successfully!', 'success')
    return redirect(url_for('events'))


# ============================================
# Resource Routes
# ============================================

@app.route('/resources')
def resources():
    """List all resources."""
    all_resources = Resource.query.order_by(Resource.type, Resource.name).all()
    return render_template('resources.html', resources=all_resources)


@app.route('/resources/add', methods=['GET', 'POST'])
def add_resource():
    """Add a new resource."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        resource_type = request.form.get('type', '').strip()
        
        # Validate required fields
        if not name or not resource_type:
            flash('Please fill in all required fields.', 'danger')
            return render_template('add_resource.html')
        
        # Validate resource type
        valid_types = ['room', 'instructor', 'equipment']
        if resource_type not in valid_types:
            flash('Invalid resource type. Choose from: room, instructor, equipment.', 'danger')
            return render_template('add_resource.html')
        
        # Create new resource
        resource = Resource(name=name, type=resource_type)
        db.session.add(resource)
        db.session.commit()
        
        flash(f'Resource "{name}" created successfully!', 'success')
        return redirect(url_for('resources'))
    
    return render_template('add_resource.html')


@app.route('/resources/edit/<int:id>', methods=['GET', 'POST'])
def edit_resource(id):
    """Edit an existing resource."""
    resource = Resource.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        resource_type = request.form.get('type', '').strip()
        
        # Validate required fields
        if not name or not resource_type:
            flash('Please fill in all required fields.', 'danger')
            return render_template('add_resource.html', resource=resource, edit_mode=True)
        
        # Validate resource type
        valid_types = ['room', 'instructor', 'equipment']
        if resource_type not in valid_types:
            flash('Invalid resource type.', 'danger')
            return render_template('add_resource.html', resource=resource, edit_mode=True)
        
        # Update resource
        resource.name = name
        resource.type = resource_type
        db.session.commit()
        
        flash(f'Resource "{name}" updated successfully!', 'success')
        return redirect(url_for('resources'))
    
    return render_template('add_resource.html', resource=resource, edit_mode=True)


@app.route('/resources/delete/<int:id>', methods=['POST'])
def delete_resource(id):
    """Delete a resource and its allocations."""
    resource = Resource.query.get_or_404(id)
    name = resource.name
    
    db.session.delete(resource)
    db.session.commit()
    
    flash(f'Resource "{name}" deleted successfully!', 'success')
    return redirect(url_for('resources'))


# ============================================
# Allocation Routes
# ============================================

@app.route('/allocate', methods=['GET', 'POST'])
def allocate():
    """Allocate resources to events with conflict detection."""
    events = Event.query.order_by(Event.start_time).all()
    resources = Resource.query.order_by(Resource.type, Resource.name).all()
    
    if request.method == 'POST':
        event_id = request.form.get('event_id')
        resource_ids = request.form.getlist('resource_ids')
        
        if not event_id:
            flash('Please select an event.', 'danger')
            return render_template('allocate.html', events=events, resources=resources)
        
        if not resource_ids:
            flash('Please select at least one resource.', 'danger')
            return render_template('allocate.html', events=events, resources=resources)
        
        event = Event.query.get(event_id)
        if not event:
            flash('Event not found.', 'danger')
            return render_template('allocate.html', events=events, resources=resources)
        
        # Check for conflicts before allocating
        conflicts_found = []
        resources_to_allocate = []
        
        for resource_id in resource_ids:
            resource = Resource.query.get(resource_id)
            if not resource:
                continue
            
            # Check if already allocated to this event
            existing = EventResourceAllocation.query.filter_by(
                event_id=event.id, 
                resource_id=resource.id
            ).first()
            
            if existing:
                flash(f'Resource "{resource.name}" is already allocated to this event.', 'warning')
                continue
            
            # Check for time conflicts
            conflicts = check_resource_conflict(
                resource.id, 
                event.start_time, 
                event.end_time
            )
            
            if conflicts:
                conflict_info = {
                    'resource': resource,
                    'conflicting_events': conflicts
                }
                conflicts_found.append(conflict_info)
            else:
                resources_to_allocate.append(resource)
        
        # If any conflicts found, show error and don't allocate any
        if conflicts_found:
            error_msg = "<strong>Conflict Detected!</strong> Cannot allocate the following resources:<br><br>"
            for cf in conflicts_found:
                error_msg += f"<strong>{cf['resource'].name}</strong> is already booked for:<br>"
                for ce in cf['conflicting_events']:
                    error_msg += f"• {ce.title} ({ce.start_time.strftime('%Y-%m-%d %H:%M')} - {ce.end_time.strftime('%H:%M')})<br>"
                error_msg += "<br>"
            flash(error_msg, 'danger')
            return render_template('allocate.html', events=events, resources=resources)
        
        # Allocate resources without conflicts
        if resources_to_allocate:
            for resource in resources_to_allocate:
                allocation = EventResourceAllocation(
                    event_id=event.id,
                    resource_id=resource.id
                )
                db.session.add(allocation)
            
            db.session.commit()
            
            allocated_names = ', '.join([r.name for r in resources_to_allocate])
            flash(f'Successfully allocated [{allocated_names}] to "{event.title}"!', 'success')
        
        return redirect(url_for('allocate'))
    
    return render_template('allocate.html', events=events, resources=resources)


@app.route('/deallocate/<int:allocation_id>', methods=['POST'])
def deallocate(allocation_id):
    """Remove a resource allocation."""
    allocation = EventResourceAllocation.query.get_or_404(allocation_id)
    
    resource_name = allocation.resource.name
    event_title = allocation.event.title
    
    db.session.delete(allocation)
    db.session.commit()
    
    flash(f'Removed "{resource_name}" from "{event_title}".', 'success')
    return redirect(url_for('allocate'))


# ============================================
# Conflict View Route
# ============================================

@app.route('/conflicts')
def conflicts():
    """Display all current conflicts in the system."""
    all_conflicts = get_all_conflicts()
    return render_template('conflicts.html', conflicts=all_conflicts)


# ============================================
# Report Route
# ============================================

@app.route('/report', methods=['GET', 'POST'])
def report():
    """Generate resource utilization report."""
    utilization_data = None
    start_date = None
    end_date = None
    
    if request.method == 'POST':
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        
        if not start_date_str or not end_date_str:
            flash('Please select both start and end dates.', 'danger')
            return render_template('report.html')
        
        try:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
            # Set end_date to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('report.html')
        
        if start_date > end_date:
            flash('Start date must be before end date.', 'danger')
            return render_template('report.html')
        
        # Calculate utilization for all resources
        resources = Resource.query.order_by(Resource.type, Resource.name).all()
        utilization_data = []
        
        for resource in resources:
            util = get_resource_utilization(resource, start_date, end_date)
            utilization_data.append(util)
        
        # Calculate max hours in date range for percentage
        total_hours_in_range = (end_date - start_date).total_seconds() / 3600
        for util in utilization_data:
            if total_hours_in_range > 0:
                util['utilization_percent'] = min(100, (util['total_hours'] / total_hours_in_range) * 100)
            else:
                util['utilization_percent'] = 0
    
    return render_template('report.html', 
                          utilization_data=utilization_data,
                          start_date=start_date,
                          end_date=end_date)


# ============================================
# Database Initialization
# ============================================

def init_db():
    """Initialize the database and create tables."""
    with app.app_context():
        db.create_all()
        print("Database initialized successfully!")


# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    # Initialize database on first run
    init_db()
    
    # Run the Flask development server
    print("=" * 50)
    print("Event Scheduling & Resource Allocation System")
    print("=" * 50)
    print("Starting server at http://127.0.0.1:5000")
    print("Press Ctrl+C to quit")
    print("=" * 50)
    
    app.run(debug=True, host='127.0.0.1', port=5000)
