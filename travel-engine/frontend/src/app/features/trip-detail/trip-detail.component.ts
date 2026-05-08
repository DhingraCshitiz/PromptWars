import { CurrencyPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { Observable, Subscriber } from 'rxjs';
import { filter, map, switchMap } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TripsService } from '../../core/services/trips.service';
import { Trip } from '../../models/trip.models';

@Component({
  selector: 'app-trip-detail',
  standalone: true,
  imports: [MatCardModule, MatButtonModule, MatProgressSpinnerModule, MatSnackBarModule, CurrencyPipe],
  templateUrl: './trip-detail.component.html',
  styleUrl: './trip-detail.component.css',
})
export class TripDetailComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly trips = inject(TripsService);
  private readonly snack = inject(MatSnackBar);

  trip: Trip | null = null;
  error: string | null = null;
  loading = true;

  constructor() {
    this.route.paramMap
      .pipe(
        map((p) => Number(p.get('id'))),
        filter((id) => !Number.isNaN(id)),
        switchMap((id) => pollingTrip$(this.trips, id)),
        takeUntilDestroyed(),
      )
      .subscribe({
        next: (e) => {
          if (e.phase === 'loading') {
            this.loading = true;
            this.error = null;
            return;
          }
          this.loading = false;
          if (e.phase === 'error') {
            this.error = e.message;
            this.trip = null;
            return;
          }
          this.error = null;
          this.trip = e.trip;
        },
      });
  }

  replan(): void {
    const id = this.trip?.id;
    if (id == null) return;
    this.trips.replanTrip(id).subscribe({
      next: () => this.snack.open('Replan queued.', 'OK', { duration: 4000 }),
      error: () => this.snack.open('Could not queue replan.', 'Dismiss', { duration: 6000 }),
    });
  }

  formatTime(value?: string | null): string {
    if (!value) return '—';
    return value.length >= 5 ? value.slice(0, 5) : value;
  }

  /** Calendar date-only API strings → dd/MM/yyyy (no UTC drift). */
  ukDate(isoLike: string): string {
    const raw = isoLike.includes('T') ? (isoLike.split('T')[0] ?? isoLike) : isoLike.slice(0, 10);
    const [y, m, d] = raw.split('-');
    if (!y || !m || !d || y.length < 4) {
      return isoLike;
    }
    return `${d}/${m}/${y}`;
  }
}

type PollEvent =
  | { phase: 'loading' }
  | { phase: 'ok'; trip: Trip }
  | { phase: 'error'; message: string };

function pollingTrip$(trips: TripsService, id: number): Observable<PollEvent> {
  return new Observable((subscriber: Subscriber<PollEvent>) => {
    let active = true;
    let settled = false;

    const emit = (e: PollEvent) => {
      if (!active) return;
      subscriber.next(e);
    };

    const fail = (message: string) => {
      if (!active || settled) return;
      settled = true;
      emit({ phase: 'error', message });
      subscriber.complete();
    };

    const succeed = (trip: Trip) => {
      emit({ phase: 'ok', trip });
      if (trip.days && trip.days.length > 0) {
        settled = true;
        subscriber.complete();
      }
    };

    emit({ phase: 'loading' });

    const tick = () => {
      if (!active || settled) return;
      trips.getTrip(id).subscribe({
        next: (trip) => succeed(trip),
        error: (err: unknown) => {
          const message = readHttpError(err);
          fail(message);
        },
      });
    };

    tick();
    const handle = window.setInterval(tick, 4500);

    return () => {
      active = false;
      window.clearInterval(handle);
    };
  });
}

function readHttpError(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    const detail =
      err.error && typeof err.error === 'object' && 'detail' in err.error
        ? (err.error as { detail: unknown }).detail
        : undefined;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => String(d)).join(', ');
    return err.message || `HTTP ${err.status}`;
  }
  return err instanceof Error ? err.message : 'Request failed';
}
