"""
models.py - Database Models for Event Scheduling & Resource Allocation System

This module defines the SQLAlchemy ORM models for:
- Event: Represents scheduled events with time windows
- Resource: Represents bookable resources (rooms, instructors, equipment)
- EventResourceAllocation: Many-to-many relationship between events and resources
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy instance
db = SQLAlchemy()


class Event(db.Model):
    """
    Event Model - Represents a scheduled event.
    
    Attributes:
        id: Primary key
        title: Event title/name
        start_time: Event start datetime
        end_time: Event end datetime
        description: Optional event description
    """
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Relationship to allocations (one-to-many)
    allocations = db.relationship('EventResourceAllocation', 
                                   back_populates='event',
                                   cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Event {self.title}>'
    
    def get_duration_hours(self):
        """Calculate event duration in hours."""
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600


class Resource(db.Model):
    """
    Resource Model - Represents a bookable resource.
    
    Attributes:
        id: Primary key
        name: Resource name
        type: Resource type (room, instructor, equipment)
    """
    __tablename__ = 'resources'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'room', 'instructor', 'equipment'
    
    # Relationship to allocations (one-to-many)
    allocations = db.relationship('EventResourceAllocation', 
                                   back_populates='resource',
                                   cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Resource {self.name} ({self.type})>'


class EventResourceAllocation(db.Model):
    """
    EventResourceAllocation Model - Many-to-many bridge table.
    
    Links events to resources, enabling:
    - Multiple resources per event
    - A resource to be used in multiple events (at different times)
    
    Attributes:
        id: Primary key
        event_id: Foreign key to events table
        resource_id: Foreign key to resources table
    """
    __tablename__ = 'event_resource_allocations'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    
    # Relationships back to parent tables
    event = db.relationship('Event', back_populates='allocations')
    resource = db.relationship('Resource', back_populates='allocations')
    
    # Unique constraint to prevent duplicate allocations
    __table_args__ = (
        db.UniqueConstraint('event_id', 'resource_id', name='unique_event_resource'),
    )
    
    def __repr__(self):
        return f'<Allocation Event:{self.event_id} Resource:{self.resource_id}>'
