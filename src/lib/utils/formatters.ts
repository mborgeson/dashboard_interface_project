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
 * Format a date to a readable string
 * @param date - The date to format
 * @param format - The format style ('short', 'medium', 'long')
 * @returns Formatted date string
 */
export function formatDate(
  date: Date,
  format: 'short' | 'medium' | 'long' = 'medium'
): string {
  const optionsMap: Record<string, Intl.DateTimeFormatOptions> = {
    short: { month: 'numeric', day: 'numeric', year: '2-digit' },
    medium: { month: 'short', day: 'numeric', year: 'numeric' },
    long: { month: 'long', day: 'numeric', year: 'numeric' },
  };

  return new Intl.DateTimeFormat('en-US', optionsMap[format]).format(date);
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
