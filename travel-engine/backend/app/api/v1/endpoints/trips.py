from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List
from app.domain.schemas import TripCreate, TripResponse
from app.services.planner import generate_trip_itinerary

router = APIRouter()

@router.post("/", response_model=TripResponse)
async def create_trip(trip_req: TripCreate, background_tasks: BackgroundTasks):
    """
    Create a new trip and queue itinerary generation.
    """
    # In a real app we'd save the trip to DB here first.
    # Then trigger async planning:
    # background_tasks.add_task(generate_trip_itinerary, trip_id)
    
    # Returning a mock structure for now
    return TripResponse(
        id=1,
        destination=trip_req.destination,
        start_date=trip_req.start_date,
        end_date=trip_req.end_date,
        preferences=trip_req.preferences,
        days=[] # Initially empty until Gemini finishes
    )

@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(trip_id: int):
    """
    Retrieve a trip's details and itinerary.
    """
    # Fetch from DB
    raise HTTPException(status_code=404, detail="Not implemented")

@router.post("/{trip_id}/replan")
async def replan_trip(trip_id: int, background_tasks: BackgroundTasks):
    """
    Trigger a re-planning of the trip.
    """
    # background_tasks.add_task(generate_trip_itinerary, trip_id)
    return {"status": "replan_queued"}
