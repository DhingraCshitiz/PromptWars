# API Contract

## Base URL
`/api/v1`

## Endpoints

### 1. Create Trip
- **URL**: `/trips/`
- **Method**: `POST`
- **Body**:
```json
{
  "destination": "string",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "preferences": {
    "budget_level": "low|medium|high",
    "travel_pace": "relaxed|moderate|fast",
    "interests": ["string"],
    "dietary_restrictions": ["string"],
    "accessibility_needs": ["string"]
  }
}
```
- **Response**: `200 OK` (Trip object)

### 2. Get Trip
- **URL**: `/trips/{trip_id}`
- **Method**: `GET`
- **Response**: `200 OK` (Trip object with populated itinerary days/stops)

### 3. Re-plan Trip
- **URL**: `/trips/{trip_id}/replan`
- **Method**: `POST`
- **Response**: `200 OK` `{"status": "replan_queued"}`
