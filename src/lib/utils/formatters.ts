import { formatDate as coreFormatDate } from '@/lib/dateUtils';

/**
 * Format a number as currency
 * @param value - The number to format
 * @param compact - Whether to use compact notation (e.g., $1.5M)
 * @returns Formatted currency string
 */
export function formatCurrency(value: number, compact = false): string {
  if (compact && value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (compact && value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format a number as a percentage
 * @param value - The number to format (0.15 = 15%)
 * @param decimals - Number of decimal places to show
 * @returns Formatted percentage string
 */
export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format a number with thousand separators
 * @param value - The number to format
 * @returns Formatted number string
 */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Format a date to a readable string.
 *
 * Delegates to the consolidated `formatDate` in `@/lib/dateUtils`.
 * Returns '--' for null/undefined to match the convention used by
 * other formatters in this module (formatCurrencyOrNA, etc.).
 *
 * @param date - The date to format
 * @param style - The format style ('short', 'medium', 'long')
 * @returns Formatted date string, or '--' for missing values
 */
export function formatDate(
  date: string | Date | null | undefined,
  style: 'short' | 'medium' | 'long' | 'numeric' = 'medium'
): string {
  return coreFormatDate(date, style) || '--';
}

/**
 * Format a number as currency, returning "N/A" when the value is zero/falsy
 * (i.e. data is missing, not actually zero).
 */
export function formatCurrencyOrNA(value: number | null | undefined, compact = false): string {
  if (value == null || value === 0) return 'N/A';
  return formatCurrency(value, compact);
}

/**
 * Format a number as a percentage, returning "N/A" when the value is zero/falsy.
 */
export function formatPercentOrNA(value: number | null | undefined, decimals = 1): string {
  if (value == null || value === 0) return 'N/A';
  return formatPercent(value, decimals);
}

/**
 * Format a number with thousand separators, returning "N/A" when zero/falsy.
 */
export function formatNumberOrNA(value: number | null | undefined): string {
  if (value == null || value === 0) return 'N/A';
  return formatNumber(value);
}

/**
 * Strip the parenthetical city/state suffix from a property name.
 * e.g. "Crestone at Shadow Mountain (Unknown, AZ)" → "Crestone at Shadow Mountain"
 * Names without a parenthetical are returned unchanged.
 */
export function shortPropertyName(name: string): string {
  return name.replace(/\s*\(.*\)\s*$/, '').trim();
}

/**
 * Format a change value with + or - sign and color class
 * @param value - The change value
 * @param isPercent - Whether to format as percentage
 * @returns Object with formatted string and color class
 */
export function formatChange(
  value: number,
  isPercent = false
): { text: string; colorClass: string } {
  const sign = value >= 0 ? '+' : '';
  const text = isPercent
    ? `${sign}${formatPercent(value)}`
    : `${sign}${formatCurrency(value, true)}`;
  const colorClass = value >= 0 ? 'text-green-600' : 'text-red-600';

  return { text, colorClass };
}
