/**
 * Shared Zod primitives for API response validation
 */
import { z } from 'zod';

/** ISO date string → Date object */
export const dateString = z.string().transform((s) => new Date(s));

/** ISO date string or null → Date | null */
export const nullableDateString = z
  .string()
  .nullable()
  .transform((s) => (s ? new Date(s) : null));

/** Numeric string from API → number */
export const numericString = z
  .string()
  .nullable()
  .transform((s) => (s ? Number(s) : 0));

/** Nullable numeric string → number | null */
export const nullableNumericString = z
  .string()
  .nullable()
  .transform((s) => (s ? Number(s) : null));
