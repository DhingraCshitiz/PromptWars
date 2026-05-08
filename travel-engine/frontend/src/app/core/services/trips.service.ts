import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Trip, TripCreate } from '../../models/trip.models';

@Injectable({ providedIn: 'root' })
export class TripsService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  createTrip(body: TripCreate): Observable<Trip> {
    return this.http.post<Trip>(`${this.base}/trips/`, body);
  }

  getTrip(id: number): Observable<Trip> {
    return this.http.get<Trip>(`${this.base}/trips/${id}`);
  }

  replanTrip(id: number): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(`${this.base}/trips/${id}/replan`, {});
  }
}
