import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatIconModule } from '@angular/material/icon';
import { TripsService } from '../../core/services/trips.service';
import { TripCreate } from '../../models/trip.models';
import { localDateToIso } from '../../core/util/iso-date';

function splitList(value: string): string[] {
  return value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

@Component({
  selector: 'app-trip-plan',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDatepickerModule,
    MatIconModule,
  ],
  templateUrl: './trip-plan.component.html',
  styleUrl: './trip-plan.component.css',
})
export class TripPlanComponent {
  private readonly fb = inject(FormBuilder);
  private readonly trips = inject(TripsService);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);

  readonly form = this.fb.nonNullable.group({
    destination: ['', Validators.required],
    start_date: [null as Date | null, Validators.required],
    end_date: [null as Date | null, Validators.required],
    budget_level: ['medium', Validators.required],
    travel_pace: ['moderate', Validators.required],
    interests: [''],
    dietary_restrictions: [''],
    accessibility_needs: [''],
  });

  submitting = false;

  readonly today = new Date(new Date().setHours(0, 0, 0, 0));

  get endMin(): Date {
    const s = this.form.controls.start_date.value;
    return s && s > this.today ? s : this.today;
  }

  submit(): void {
    if (this.form.invalid || this.submitting) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const start = v.start_date!;
    const end = v.end_date!;
    if (end < start) {
      this.snack.open('End date must be on or after start date.', 'Dismiss', { duration: 5000 });
      return;
    }

    const body: TripCreate = {
      destination: v.destination.trim(),
      start_date: localDateToIso(start),
      end_date: localDateToIso(end),
      preferences: {
        budget_level: v.budget_level,
        travel_pace: v.travel_pace,
        interests: splitList(v.interests),
        dietary_restrictions: splitList(v.dietary_restrictions),
        accessibility_needs: splitList(v.accessibility_needs),
      },
    };

    this.submitting = true;
    this.trips.createTrip(body).subscribe({
      next: (trip) => {
        this.submitting = false;
        this.snack.open('Trip created. Generating itinerary…', 'OK', { duration: 4000 });
        void this.router.navigate(['/trips', trip.id]);
      },
      error: (err: unknown) => {
        this.submitting = false;
        const msg =
          err && typeof err === 'object' && 'error' in err && err.error && typeof err.error === 'object' && 'detail' in err.error
            ? String((err as { error: { detail: unknown } }).error.detail)
            : 'Could not create trip. Is the API running on port 8000?';
        this.snack.open(msg, 'Dismiss', { duration: 8000 });
      },
    });
  }
}
