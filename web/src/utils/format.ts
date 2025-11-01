/**
 * Formatting utilities
 */

import { format, formatDistanceToNow, parseISO } from 'date-fns';

/**
 * Format a number as currency
 */
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format a number as percentage
 */
export function formatPercentage(value: number | null | undefined, decimals: number = 0): string {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format a number with commas
 */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Format a date string
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  try {
    return format(parseISO(dateString), 'MMM d, yyyy');
  } catch {
    return 'Invalid date';
  }
}

/**
 * Format a datetime string
 */
export function formatDateTime(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  try {
    return format(parseISO(dateString), 'MMM d, yyyy h:mm a');
  } catch {
    return 'Invalid date';
  }
}

/**
 * Format a date as relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  try {
    return formatDistanceToNow(parseISO(dateString), { addSuffix: true });
  } catch {
    return 'Invalid date';
  }
}

/**
 * Format confidence score as percentage with color
 */
export function formatConfidence(confidence: number | null | undefined): {
  text: string;
  color: string;
} {
  if (confidence === null || confidence === undefined) {
    return { text: 'N/A', color: 'text-gray-500' };
  }

  const percentage = Math.round(confidence * 100);
  let color = 'text-gray-500';

  if (percentage >= 90) color = 'text-green-600';
  else if (percentage >= 75) color = 'text-blue-600';
  else if (percentage >= 50) color = 'text-yellow-600';
  else color = 'text-red-600';

  return {
    text: `${percentage}%`,
    color,
  };
}

/**
 * Get method badge color
 */
export function getMethodColor(method: string | null | undefined): string {
  switch (method) {
    case 'api':
      return 'bg-green-100 text-green-800';
    case 'scrape':
      return 'bg-blue-100 text-blue-800';
    case 'manual':
      return 'bg-purple-100 text-purple-800';
    case 'computed':
      return 'bg-yellow-100 text-yellow-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

/**
 * Capitalize first letter
 */
export function capitalize(str: string | null | undefined): string {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Convert field_path to readable label (e.g., "listing_price" -> "Listing Price")
 */
export function fieldPathToLabel(fieldPath: string): string {
  return fieldPath
    .split('_')
    .map((word) => capitalize(word))
    .join(' ');
}

/**
 * Format a value based on field type
 */
export function formatFieldValue(fieldPath: string, value: any): string {
  if (value === null || value === undefined) return 'N/A';

  // Check field name for type hints
  const path = fieldPath.toLowerCase();

  if (path.includes('price') || path.includes('value') || path.includes('amount')) {
    return formatCurrency(value);
  }

  if (path.includes('date') && typeof value === 'string') {
    return formatDate(value);
  }

  if (path.includes('pct') || path.includes('percentage')) {
    return formatPercentage(value / 100);
  }

  if (typeof value === 'number') {
    return formatNumber(value);
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }

  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(', ') : 'None';
  }

  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  return String(value);
}

/**
 * Check if a field is stale (extracted more than 30 days ago)
 */
export function isStale(extractedAt: string | null | undefined, thresholdDays: number = 30): boolean {
  if (!extractedAt) return false;

  try {
    const date = parseISO(extractedAt);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    return diffDays > thresholdDays;
  } catch {
    return false;
  }
}
