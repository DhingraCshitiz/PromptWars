import { Routes } from '@angular/router';
import { TripPlanComponent } from './features/trip-plan/trip-plan.component';
import { TripDetailComponent } from './features/trip-detail/trip-detail.component';

export const routes: Routes = [
  { path: '', component: TripPlanComponent, title: 'Plan new trip' },
  { path: 'trips/:id', component: TripDetailComponent, title: 'Trip' },
  { path: '**', redirectTo: '' },
];
