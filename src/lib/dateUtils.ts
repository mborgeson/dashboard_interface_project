/**
 * Consolidated date/time formatting utilities.
 *
 * All functions accept nullable/undefined inputs and return safe defaults
 * (empty string or null) — they never throw on bad input.
 */

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

/**
 * Safely parse a date string (or pass through a Date).
 * Returns null for null, undefined, or unparseable values.
 */
export function parseDate(value: string | Date | null | undefined): Date | null {
  if (value == null) return null;
  if (value instanceof Date) {
    return isNaN(value.getTime()) ? null : value;
  }
  const parsed = new Date(value);
  return isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * Type-guard: returns true if `value` can be interpreted as a valid Date.
 */
export function isValidDate(value: unknown): boolean {
  if (value == null) return false;
  if (value instanceof Date) return !isNaN(value.getTime());
  if (typeof value === 'string') {
    const d = new Date(value);
    return !isNaN(d.getTime());
  }
  if (typeof value === 'number') {
    return !isNaN(new Date(value).getTime());
  }
  return false;
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

/**
 * Standard display date — e.g. "Mar 10, 2026"
 *
 * Replaces scattered `toLocaleDateString('en-US', { month: 'short', … })`
 * calls across the codebase.
 */
export function formatDate(
  date: string | Date | null | undefined,
  style: 'short' | 'medium' | 'long' = 'medium',
): string {
  const d = parseDate(date);
  if (!d) return '';

  const optionsMap: Record<string, Intl.DateTimeFormatOptions> = {
    short: { month: 'numeric', day: 'numeric', year: '2-digit' },
    medium: { month: 'short', day: 'numeric', year: 'numeric' },
    long: { month: 'long', day: 'numeric', year: 'numeric' },
  };

  return new Intl.DateTimeFormat('en-US', optionsMap[style]).format(d);
}

/**
 * Date with time — e.g. "Mar 10, 2026 2:30 PM"
 */
export function formatDateTime(
  date: string | Date | null | undefined,
): string {
  const d = parseDate(date);
  if (!d) return '';

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(d);
}

/**
 * Time only — e.g. "2:30 PM"
 */
export function formatTime(
  date: string | Date | null | undefined,
): string {
  const d = parseDate(date);
  if (!d) return '';

  return d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

/**
 * Human-friendly relative time — "just now", "5m ago", "3h ago", "2d ago",
 * then falls back to a short date for anything older than 7 days.
 *
 * Consolidates the duplicate `formatTimeAgo` helpers that existed in
 * ActivityItem, PropertyActivityItem, and ReportQueue.
 */
export function formatRelativeTime(
  date: string | Date | null | undefined,
): string {
  const d = parseDate(date);
  if (!d) return '';

  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMs / 3_600_000);
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  // Older than a week — show a compact date, omit year if same as current
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: sameYear ? undefined : 'numeric',
  });
}

/**
 * Classify a date into a human-friendly group label for timeline UIs:
 * "Today", "Yesterday", a weekday name (within 7 days), or a long date.
 *
 * Consolidates the duplicate `getDateGroup` helpers that existed in
 * ActivityTimeline and PropertyActivityTimeline.
 */
export function getDateGroupLabel(date: string | Date | null | undefined): string {
  const d = parseDate(date);
  if (!d) return '';

  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate());

  if (target.getTime() === today.getTime()) return 'Today';
  if (target.getTime() === yesterday.getTime()) return 'Yesterday';

  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);
  if (target > weekAgo) {
    return d.toLocaleDateString('en-US', { weekday: 'long' });
  }

  return d.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  });
}
