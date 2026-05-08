from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, time

class TripPreferenceBase(BaseModel):
    budget_level: str = Field(..., description="low, medium, high")
    travel_pace: str = Field(..., description="relaxed, moderate, fast")
    interests: List[str] = Field(default_factory=list)
    dietary_restrictions: List[str] = Field(default_factory=list)
    accessibility_needs: List[str] = Field(default_factory=list)

class TripCreate(BaseModel):
    destination: str
    start_date: date
    end_date: date
    preferences: TripPreferenceBase

class ItineraryStopResponse(BaseModel):
    id: int
    place_id: str
    name: str
    description: str
    start_time: Optional[time]
    end_time: Optional[time]
    cost_estimate: Optional[float]
    
    class Config:
        from_attributes = True

class ItineraryDayResponse(BaseModel):
    id: int
    date: date
    day_index: int
    stops: List[ItineraryStopResponse]
    
    class Config:
        from_attributes = True

class TripResponse(BaseModel):
    id: int
    destination: str
    start_date: date
    end_date: date
    preferences: TripPreferenceBase
    days: List[ItineraryDayResponse] = []
    
    class Config:
        from_attributes = True
