import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base

Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True) # Firebase UID
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    trips: Mapped[List["Trip"]] = relationship(back_populates="user")

class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user_profiles.id"))
    destination: Mapped[str] = mapped_column(String)
    start_date: Mapped[datetime.date] = mapped_column(DateTime)
    end_date: Mapped[datetime.date] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    user: Mapped["UserProfile"] = relationship(back_populates="trips")
    preferences: Mapped["TripPreference"] = relationship(back_populates="trip", uselist=False)
    days: Mapped[List["ItineraryDay"]] = relationship(back_populates="trip", cascade="all, delete-orphan")

class TripPreference(Base):
    __tablename__ = "trip_preferences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(Integer, ForeignKey("trips.id"))
    budget_level: Mapped[str] = mapped_column(String) # low, medium, high
    travel_pace: Mapped[str] = mapped_column(String) # relaxed, moderate, fast
    interests: Mapped[list[str]] = mapped_column(JSON)
    dietary_restrictions: Mapped[list[str]] = mapped_column(JSON)
    accessibility_needs: Mapped[list[str]] = mapped_column(JSON)
    
    trip: Mapped["Trip"] = relationship(back_populates="preferences")

class ItineraryDay(Base):
    __tablename__ = "itinerary_days"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(Integer, ForeignKey("trips.id"))
    date: Mapped[datetime.date] = mapped_column(DateTime)
    day_index: Mapped[int] = mapped_column(Integer)
    
    trip: Mapped["Trip"] = relationship(back_populates="days")
    stops: Mapped[List["ItineraryStop"]] = relationship(back_populates="day", cascade="all, delete-orphan")

class ItineraryStop(Base):
    __tablename__ = "itinerary_stops"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day_id: Mapped[int] = mapped_column(Integer, ForeignKey("itinerary_days.id"))
    order_index: Mapped[int] = mapped_column(Integer)
    place_id: Mapped[str] = mapped_column(String) # Google Place ID
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    start_time: Mapped[Optional[datetime.time]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime.time]] = mapped_column(DateTime, nullable=True)
    cost_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    day: Mapped["ItineraryDay"] = relationship(back_populates="stops")
