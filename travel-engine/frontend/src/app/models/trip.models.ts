export interface TripPreference {
  budget_level: string;
  travel_pace: string;
  interests: string[];
  dietary_restrictions: string[];
  accessibility_needs: string[];
}

export interface TripCreate {
  destination: string;
  start_date: string;
  end_date: string;
  preferences: TripPreference;
}

export interface ItineraryStop {
  id: number;
  place_id: string;
  name: string;
  description: string;
  start_time?: string | null;
  end_time?: string | null;
  cost_estimate?: number | null;
}

export interface ItineraryDay {
  id: number;
  date: string;
  day_index: number;
  stops: ItineraryStop[];
}

export interface Trip {
  id: number;
  destination: string;
  start_date: string;
  end_date: string;
  preferences: TripPreference;
  days: ItineraryDay[];
}
