import datetime
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.domain.models import ItineraryDay, ItineraryStop, Trip
from app.integrations.gemini import get_planner_client


def as_date(value: datetime.date | datetime.datetime) -> datetime.date:
    if isinstance(value, datetime.datetime):
        return value.date()
    return value


async def generate_trip_itinerary(trip_id: int):
    """
    Background job to plan the trip.
    """
    async with SessionLocal() as db:
        result = await db.execute(
            select(Trip)
            .options(
                selectinload(Trip.preferences),
                selectinload(Trip.days).selectinload(ItineraryDay.stops),
            )
            .where(Trip.id == trip_id),
        )
        trip = result.scalars().first()
        if not trip:
            return

        client = get_planner_client()

        start_date = as_date(trip.start_date)
        end_date = as_date(trip.end_date)
        day_count = (end_date - start_date).days + 1

        constraints = {
            "destination": trip.destination,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "days": day_count,
            "preferences": {
                "budget": trip.preferences.budget_level,
                "pace": trip.preferences.travel_pace,
                "interests": trip.preferences.interests,
                "dietary_restrictions": trip.preferences.dietary_restrictions,
                "accessibility_needs": trip.preferences.accessibility_needs,
            },
        }

        try:
            itinerary_data = await client.generate_itinerary(constraints)

            trip.days.clear()

            for day_data in itinerary_data.get("days", []):
                raw_idx = int(day_data.get("day_index", 1))
                day_offset = max(0, raw_idx - 1)
                if day_offset >= day_count:
                    continue

                db_day = ItineraryDay(
                    trip_id=trip.id,
                    day_index=day_offset,
                    date=start_date + timedelta(days=day_offset),
                )
                for order_index, stop_data in enumerate(day_data.get("stops", [])):
                    db_stop = ItineraryStop(
                        name=stop_data["name"],
                        description=stop_data["description"],
                        place_id=stop_data.get("place_id", "manual"),
                        order_index=order_index,
                    )
                    db_day.stops.append(db_stop)
                trip.days.append(db_day)

            await db.commit()
            print(f"Successfully generated itinerary for trip {trip_id}")

        except Exception as e:
            print(f"Error generating itinerary for trip {trip_id}: {str(e)}")
            await db.rollback()
