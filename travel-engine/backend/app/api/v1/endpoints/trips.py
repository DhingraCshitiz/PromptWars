from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.domain.models import ItineraryDay, Trip, TripPreference
from app.domain.schemas import TripCreate, TripResponse
from app.services.planner import generate_trip_itinerary

router = APIRouter()


async def load_trip_graph(db: AsyncSession, trip_id: int) -> Trip | None:
    result = await db.execute(
        select(Trip)
        .options(
            selectinload(Trip.preferences),
            selectinload(Trip.days).selectinload(ItineraryDay.stops),
        )
        .where(Trip.id == trip_id),
    )
    return result.scalars().first()


@router.post("/", response_model=TripResponse)
async def create_trip(
    trip_req: TripCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new trip and queue itinerary generation.
    """
    db_trip = Trip(
        user_id="anonymous",
        destination=trip_req.destination,
        start_date=trip_req.start_date,
        end_date=trip_req.end_date,
    )
    db.add(db_trip)
    await db.flush()

    db_prefs = TripPreference(
        trip_id=db_trip.id,
        budget_level=trip_req.preferences.budget_level,
        travel_pace=trip_req.preferences.travel_pace,
        interests=trip_req.preferences.interests,
        dietary_restrictions=trip_req.preferences.dietary_restrictions,
        accessibility_needs=trip_req.preferences.accessibility_needs,
    )
    db.add(db_prefs)
    await db.commit()

    created = await load_trip_graph(db, db_trip.id)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to load created trip")

    background_tasks.add_task(generate_trip_itinerary, db_trip.id)

    return created


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(trip_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a trip's details and itinerary.
    """
    db_trip = await load_trip_graph(db, trip_id)
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return db_trip


@router.post("/{trip_id}/replan")
async def replan_trip(
    trip_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a re-planning of the trip.
    """
    exists = await db.scalar(select(Trip.id).where(Trip.id == trip_id))
    if exists is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    background_tasks.add_task(generate_trip_itinerary, trip_id)
    return {"status": "replan_queued"}
