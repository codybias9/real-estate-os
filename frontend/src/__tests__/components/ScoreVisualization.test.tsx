/**
 * Tests for ScoreVisualization component
 */

import { render, screen } from '@testing-library/react';
import { ScoreVisualization } from '@/components/ScoreVisualization';
import type { ScoreResult } from '@/types';

describe('ScoreVisualization', () => {
  const mockScoreResult: ScoreResult = {
    property_id: 'prop-123',
    score: 78,
    reasons: [
      {
        feature: 'property_condition',
        weight: 0.3,
        direction: 'positive' as const,
        note: 'Excellent condition (built 2010, 15 years old)',
      },
      {
        feature: 'location_quality',
        weight: 0.25,
        direction: 'positive' as const,
        note: 'Prime location (central Las Vegas)',
      },
      {
        feature: 'value_potential',
        weight: 0.2,
        direction: 'negative' as const,
        note: 'Below market value',
      },
    ],
    model_version: 'deterministic-v1',
    scored_at: '2025-11-02T12:00:00Z',
  };

  it('shows loading spinner when loading', () => {
    render(<ScoreVisualization score={undefined} scoreResult={undefined} isLoading={true} />);

    expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
  });

  it('shows "not scored" message when no score exists', () => {
    render(<ScoreVisualization score={undefined} scoreResult={undefined} isLoading={false} />);

    expect(screen.getByText(/Property has not been scored yet/i)).toBeInTheDocument();
  });

  it('renders score badge with correct value', () => {
    render(<ScoreVisualization score={78} scoreResult={mockScoreResult} isLoading={false} />);

    expect(screen.getByText('78')).toBeInTheDocument();
    expect(screen.getByText(/Good Investment/i)).toBeInTheDocument();
  });

  it('displays model version', () => {
    render(<ScoreVisualization score={78} scoreResult={mockScoreResult} isLoading={false} />);

    expect(screen.getByText(/Model: deterministic-v1/i)).toBeInTheDocument();
  });

  it('renders all score reasons', () => {
    render(<ScoreVisualization score={78} scoreResult={mockScoreResult} isLoading={false} />);

    expect(screen.getByText(/Property condition/i)).toBeInTheDocument();
    expect(screen.getByText(/Location quality/i)).toBeInTheDocument();
    expect(screen.getByText(/Value potential/i)).toBeInTheDocument();
  });

  it('displays weight percentages correctly', () => {
    render(<ScoreVisualization score={78} scoreResult={mockScoreResult} isLoading={false} />);

    expect(screen.getByText('30% weight')).toBeInTheDocument();
    expect(screen.getByText('25% weight')).toBeInTheDocument();
    expect(screen.getByText('20% weight')).toBeInTheDocument();
  });

  it('shows reason notes', () => {
    render(<ScoreVisualization score={78} scoreResult={mockScoreResult} isLoading={false} />);

    expect(screen.getByText(/Excellent condition/i)).toBeInTheDocument();
    expect(screen.getByText(/Prime location/i)).toBeInTheDocument();
    expect(screen.getByText(/Below market value/i)).toBeInTheDocument();
  });

  it('applies correct styling for positive direction', () => {
    render(<ScoreVisualization score={78} scoreResult={mockScoreResult} isLoading={false} />);

    const positiveReasons = screen.getAllByText('↑');
    expect(positiveReasons.length).toBeGreaterThan(0);
    expect(positiveReasons[0]).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('applies correct styling for negative direction', () => {
    render(<ScoreVisualization score={78} scoreResult={mockScoreResult} isLoading={false} />);

    const negativeReason = screen.getByText('↓');
    expect(negativeReason).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('shows correct score label for different score ranges', () => {
    const { rerender } = render(
      <ScoreVisualization score={85} scoreResult={{ ...mockScoreResult, score: 85 }} isLoading={false} />
    );
    expect(screen.getByText(/Excellent Investment/i)).toBeInTheDocument();

    rerender(
      <ScoreVisualization score={65} scoreResult={{ ...mockScoreResult, score: 65 }} isLoading={false} />
    );
    expect(screen.getByText(/Good Investment/i)).toBeInTheDocument();

    rerender(
      <ScoreVisualization score={45} scoreResult={{ ...mockScoreResult, score: 45 }} isLoading={false} />
    );
    expect(screen.getByText(/Fair Investment/i)).toBeInTheDocument();

    rerender(
      <ScoreVisualization score={25} scoreResult={{ ...mockScoreResult, score: 25 }} isLoading={false} />
    );
    expect(screen.getByText(/Poor Investment/i)).toBeInTheDocument();
  });
});
