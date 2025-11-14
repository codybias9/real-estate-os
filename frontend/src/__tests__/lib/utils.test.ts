/**
 * Tests for utility functions
 */

import {
  formatCurrency,
  formatNumber,
  formatRelativeDate,
  formatDate,
  getScoreColor,
  getScoreBadgeColor,
  getStateBadgeColor,
  getInitials,
  truncate,
} from '@/lib/utils';

describe('formatCurrency', () => {
  it('formats numbers as USD currency', () => {
    expect(formatCurrency(1234567)).toBe('$1,234,567');
    expect(formatCurrency(100)).toBe('$100');
    expect(formatCurrency(0)).toBe('$0');
  });

  it('handles undefined values', () => {
    expect(formatCurrency(undefined)).toBe('N/A');
  });
});

describe('formatNumber', () => {
  it('formats numbers with commas', () => {
    expect(formatNumber(1234567)).toBe('1,234,567');
    expect(formatNumber(1000)).toBe('1,000');
    expect(formatNumber(100)).toBe('100');
  });

  it('handles undefined values', () => {
    expect(formatNumber(undefined)).toBe('N/A');
  });
});

describe('formatRelativeDate', () => {
  const now = new Date('2025-11-02T12:00:00Z');
  beforeAll(() => {
    jest.useFakeTimers();
    jest.setSystemTime(now);
  });

  afterAll(() => {
    jest.useRealTimers();
  });

  it('formats dates as "just now" for < 1 minute', () => {
    const date = new Date('2025-11-02T11:59:30Z').toISOString();
    expect(formatRelativeDate(date)).toBe('just now');
  });

  it('formats dates as minutes ago', () => {
    const date = new Date('2025-11-02T11:50:00Z').toISOString();
    expect(formatRelativeDate(date)).toBe('10m ago');
  });

  it('formats dates as hours ago', () => {
    const date = new Date('2025-11-02T09:00:00Z').toISOString();
    expect(formatRelativeDate(date)).toBe('3h ago');
  });

  it('formats dates as days ago', () => {
    const date = new Date('2025-10-30T12:00:00Z').toISOString();
    expect(formatRelativeDate(date)).toBe('3d ago');
  });

  it('formats old dates as full date', () => {
    const date = new Date('2025-10-01T12:00:00Z').toISOString();
    const result = formatRelativeDate(date);
    expect(result).toMatch(/Oct/);
  });
});

describe('getScoreColor', () => {
  it('returns green for excellent scores (80+)', () => {
    expect(getScoreColor(85)).toContain('green');
    expect(getScoreColor(100)).toContain('green');
  });

  it('returns blue for good scores (60-79)', () => {
    expect(getScoreColor(70)).toContain('blue');
    expect(getScoreColor(60)).toContain('blue');
  });

  it('returns yellow for fair scores (40-59)', () => {
    expect(getScoreColor(50)).toContain('yellow');
    expect(getScoreColor(40)).toContain('yellow');
  });

  it('returns red for poor scores (< 40)', () => {
    expect(getScoreColor(30)).toContain('red');
    expect(getScoreColor(0)).toContain('red');
  });
});

describe('getScoreBadgeColor', () => {
  it('returns correct badge colors for score ranges', () => {
    expect(getScoreBadgeColor(85)).toBe('bg-green-500');
    expect(getScoreBadgeColor(70)).toBe('bg-blue-500');
    expect(getScoreBadgeColor(50)).toBe('bg-yellow-500');
    expect(getScoreBadgeColor(30)).toBe('bg-red-500');
  });
});

describe('getStateBadgeColor', () => {
  it('returns correct colors for each state', () => {
    expect(getStateBadgeColor('discovered')).toContain('gray');
    expect(getStateBadgeColor('enriched')).toContain('blue');
    expect(getStateBadgeColor('scored')).toContain('purple');
    expect(getStateBadgeColor('memo_generated')).toContain('indigo');
    expect(getStateBadgeColor('contacted')).toContain('orange');
    expect(getStateBadgeColor('responded')).toContain('green');
  });

  it('returns default color for unknown states', () => {
    expect(getStateBadgeColor('unknown')).toContain('gray');
  });
});

describe('getInitials', () => {
  it('returns initials from full name', () => {
    expect(getInitials('John Doe')).toBe('JD');
    expect(getInitials('Jane Smith')).toBe('JS');
  });

  it('handles single names', () => {
    expect(getInitials('Madonna')).toBe('M');
  });

  it('returns only first two initials for long names', () => {
    expect(getInitials('John Paul Jones Smith')).toBe('JP');
  });
});

describe('truncate', () => {
  it('truncates text longer than max length', () => {
    expect(truncate('This is a very long text', 10)).toBe('This is a ...');
  });

  it('does not truncate text shorter than max length', () => {
    expect(truncate('Short', 10)).toBe('Short');
  });

  it('handles exact length', () => {
    expect(truncate('Exactly10!', 10)).toBe('Exactly10!');
  });
});
