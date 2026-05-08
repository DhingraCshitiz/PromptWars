import { Inject, Injectable, Optional } from '@angular/core';
import { MAT_DATE_LOCALE, NativeDateAdapter } from '@angular/material/core';

/** Material date adapter: display and parse as dd/MM/yyyy (UK). */
@Injectable()
export class UkDdMmYyyyDateAdapter extends NativeDateAdapter {
  constructor(@Optional() @Inject(MAT_DATE_LOCALE) dateLocale?: string) {
    super(dateLocale ?? 'en-GB');
  }

  override format(date: Date): string {
    const d = String(date.getDate()).padStart(2, '0');
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const y = date.getFullYear();
    return `${d}/${m}/${y}`;
  }

  override parse(value: unknown): Date | null {
    if (value == null || typeof value !== 'string') {
      return null;
    }
    const s = value.trim();
    if (!s) return null;
    const sep = ['/', '-', '.'].find((c) => s.includes(c)) ?? '/';
    const parts = s.split(sep).map((p) => p.trim());
    if (parts.length !== 3) {
      return null;
    }
    const day = Number(parts[0]);
    const month = Number(parts[1]) - 1;
    let year = Number(parts[2]);
    if (
      Number.isNaN(day) ||
      Number.isNaN(month) ||
      Number.isNaN(year) ||
      month < 0 ||
      month > 11 ||
      day < 1 ||
      day > 31
    ) {
      return null;
    }
    if (year < 100) {
      year += 2000;
    }
    const d = new Date(year, month, day);
    if (d.getFullYear() !== year || d.getMonth() !== month || d.getDate() !== day) {
      return null;
    }
    return d;
  }
}
