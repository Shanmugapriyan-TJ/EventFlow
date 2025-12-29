from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Event, Resource, EventResourceAllocation
from datetime import datetime
from sqlalchemy import and_, or_

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def times_overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def check_resource_conflict(resource_id, start_time, end_time, exclude_event_id=None):
    conflicts = []
    allocations = EventResourceAllocation.query.filter_by(resource_id=resource_id).all()
    for allocation in allocations:
        if exclude_event_id and allocation.event_id == exclude_event_id:
            continue
        event = allocation.event
        if times_overlap(start_time, end_time, event.start_time, event.end_time):
            conflicts.append(event)
    return conflicts

def validate_event_times(start_time, end_time):
    if start_time >= end_time:
        return False, "End time must be after start time. Events with zero duration are not allowed."
    return True, None

def get_all_conflicts():
    conflicts = []
    resources = Resource.query.all()
    for resource in resources:
        allocations = EventResourceAllocation.query.filter_by(resource_id=resource.id).all()
        events = [a.event for a in allocations]
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
    allocations = EventResourceAllocation.query.filter_by(resource_id=resource.id).all()
    total_hours = 0
    upcoming_bookings = []
    now = datetime.now()
    for allocation in allocations:
        event = allocation.event
        event_start = max(event.start_time, start_date)
        event_end = min(event.end_time, end_date)
        if event_start < event_end:
            hours = (event_end - event_start).total_seconds() / 3600
            total_hours += hours
        if event.start_time > now:
            upcoming_bookings.append(event)
    upcoming_bookings.sort(key=lambda e: e.start_time)
    return {
        'resource': resource,
        'total_hours': round(total_hours, 2),
        'upcoming_bookings': upcoming_bookings
    }

@app.route('/')
def index():
    events_count = Event.query.count()
    resources_count = Resource.query.count()
    recent_events = Event.query.order_by(Event.start_time.desc()).limit(5).all()
    return render_template(
        'base.html',
        events_count=events_count,
        resources_count=resources_count,
        recent_events=recent_events,
        is_home=True
    )

@app.route('/events')
def events():
    all_events = Event.query.order_by(Event.start_time).all()
    return render_template('events.html', events=all_events)

@app.route('/events/add', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        start_time_str = request.form.get('start_time', '')
        end_time_str = request.form.get('end_time', '')
        if not title or not start_time_str or not end_time_str:
            flash('Please fill in all required fields.', 'danger')
            return render_template('add_event.html')
        try:
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return render_template('add_event.html')
        is_valid, error_msg = validate_event_times(start_time, end_time)
        if not is_valid:
            flash(error_msg, 'danger')
            return render_template('add_event.html')
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
    event = Event.query.get_or_404(id)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        start_time_str = request.form.get('start_time', '')
        end_time_str = request.form.get('end_time', '')
        if not title or not start_time_str or not end_time_str:
            flash('Please fill in all required fields.', 'danger')
            return render_template('edit_event.html', event=event)
        try:
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return render_template('edit_event.html', event=event)
        is_valid, error_msg = validate_event_times(start_time, end_time)
        if not is_valid:
            flash(error_msg, 'danger')
            return render_template('edit_event.html', event=event)
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
                error_msg = "Cannot update event times.<br>"
                for cr in conflict_resources:
                    names = ', '.join([e.title for e in cr['conflicting_events']])
                    error_msg += f"<strong>{cr['resource'].name}</strong> conflicts with: {names}<br>"
                flash(error_msg, 'danger')
                return render_template('edit_event.html', event=event)
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
    event = Event.query.get_or_404(id)
    title = event.title
    db.session.delete(event)
    db.session.commit()
    flash(f'Event "{title}" deleted successfully!', 'success')
    return redirect(url_for('events'))

@app.route('/resources')
def resources():
    all_resources = Resource.query.order_by(Resource.type, Resource.name).all()
    return render_template('resources.html', resources=all_resources)

@app.route('/resources/add', methods=['GET', 'POST'])
def add_resource():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        resource_type = request.form.get('type', '').strip()
        if not name or not resource_type:
            flash('Please fill in all required fields.', 'danger')
            return render_template('add_resource.html')
        if resource_type not in ['room', 'instructor', 'equipment']:
            flash('Invalid resource type.', 'danger')
            return render_template('add_resource.html')
        resource = Resource(name=name, type=resource_type)
        db.session.add(resource)
        db.session.commit()
        flash(f'Resource "{name}" created successfully!', 'success')
        return redirect(url_for('resources'))
    return render_template('add_resource.html')

@app.route('/resources/edit/<int:id>', methods=['GET', 'POST'])
def edit_resource(id):
    resource = Resource.query.get_or_404(id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        resource_type = request.form.get('type', '').strip()
        if not name or not resource_type:
            flash('Please fill in all required fields.', 'danger')
            return render_template('add_resource.html', resource=resource, edit_mode=True)
        if resource_type not in ['room', 'instructor', 'equipment']:
            flash('Invalid resource type.', 'danger')
            return render_template('add_resource.html', resource=resource, edit_mode=True)
        resource.name = name
        resource.type = resource_type
        db.session.commit()
        flash(f'Resource "{name}" updated successfully!', 'success')
        return redirect(url_for('resources'))
    return render_template('add_resource.html', resource=resource, edit_mode=True)

@app.route('/resources/delete/<int:id>', methods=['POST'])
def delete_resource(id):
    resource = Resource.query.get_or_404(id)
    name = resource.name
    db.session.delete(resource)
    db.session.commit()
    flash(f'Resource "{name}" deleted successfully!', 'success')
    return redirect(url_for('resources'))

@app.route('/allocate', methods=['GET', 'POST'])
def allocate():
    events = Event.query.order_by(Event.start_time).all()
    resources = Resource.query.order_by(Resource.type, Resource.name).all()
    if request.method == 'POST':
        event_id = request.form.get('event_id')
        resource_ids = request.form.getlist('resource_ids')
        if not event_id or not resource_ids:
            flash('Please select event and resources.', 'danger')
            return render_template('allocate.html', events=events, resources=resources)
        event = Event.query.get(event_id)
        conflicts_found = []
        resources_to_allocate = []
        for rid in resource_ids:
            resource = Resource.query.get(rid)
            if not resource:
                continue
            existing = EventResourceAllocation.query.filter_by(
                event_id=event.id, resource_id=resource.id
            ).first()
            if existing:
                continue
            conflicts = check_resource_conflict(resource.id, event.start_time, event.end_time)
            if conflicts:
                conflicts_found.append({'resource': resource, 'conflicting_events': conflicts})
            else:
                resources_to_allocate.append(resource)
        if conflicts_found:
            flash('Conflict detected. Allocation aborted.', 'danger')
            return render_template('allocate.html', events=events, resources=resources)
        for resource in resources_to_allocate:
            db.session.add(EventResourceAllocation(event_id=event.id, resource_id=resource.id))
        db.session.commit()
        flash('Resources allocated successfully!', 'success')
        return redirect(url_for('allocate'))
    return render_template('allocate.html', events=events, resources=resources)

@app.route('/deallocate/<int:allocation_id>', methods=['POST'])
def deallocate(allocation_id):
    allocation = EventResourceAllocation.query.get_or_404(allocation_id)
    db.session.delete(allocation)
    db.session.commit()
    flash('Allocation removed successfully.', 'success')
    return redirect(url_for('allocate'))



@app.route('/report', methods=['GET', 'POST'])
def report():
    utilization_data = None
    start_date = None
    end_date = None
    if request.method == 'POST':
        start_date = datetime.fromisoformat(request.form.get('start_date'))
        end_date = datetime.fromisoformat(request.form.get('end_date')).replace(hour=23, minute=59, second=59)
        resources = Resource.query.all()
        utilization_data = []
        for resource in resources:
            util = get_resource_utilization(resource, start_date, end_date)
            total_hours = (end_date - start_date).total_seconds() / 3600
            util['utilization_percent'] = (util['total_hours'] / total_hours) * 100 if total_hours else 0
            utilization_data.append(util)
    return render_template('report.html', utilization_data=utilization_data,
                           start_date=start_date, end_date=end_date)

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
