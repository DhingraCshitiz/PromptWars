from app.integrations.gemini import GeminiPlannerClient

async def generate_trip_itinerary(trip_id: int):
    """
    Background job to plan the trip.
    1. Fetch trip and preferences from DB.
    2. Call GeminiPlannerClient.
    3. Save generated itinerary to DB.
    4. Trigger notification to user.
    """
    client = GeminiPlannerClient()
    
    # Mock constraints
    constraints = {
        "destination": "Paris",
        "days": 3,
        "preferences": {"budget": "medium"}
    }
    
    itinerary_data = await client.generate_itinerary(constraints)
    
    # Save to DB...
    print(f"Generated itinerary for trip {trip_id}: {itinerary_data}")
