/**
 * Tests for PropertyDrawer component
 *
 * Tests:
 * - Property details rendering
 * - Tab navigation
 * - Scorecard display
 * - Provenance data
 */

import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, setupUser } from '../test/utils';
import { PropertyDrawer } from './PropertyDrawer';

describe('PropertyDrawer', () => {
  const mockProperty = {
    id: 'prop-123',
    canonical_address: {
      street: '123 Main St',
      city: 'San Francisco',
      state: 'CA',
      zip: '94102',
    },
    listing_price: 500000,
    square_feet: 2000,
    bedrooms: 3,
    bathrooms: 2,
    year_built: 2020,
  };

  const mockScorecard = {
    id: 'score-123',
    score: 0.82,
    grade: 'B+',
    model_version: 'v1.0.0',
    explainability: [
      {
        factor_name: 'location',
        factor_weight: 0.4,
        contribution: 0.35,
        explanation: 'Great neighborhood',
      },
    ],
  };

  it('renders property details', () => {
    renderWithProviders(
      <PropertyDrawer
        propertyId={mockProperty.id}
        isOpen={true}
        onClose={() => {}}
      />
    );

    expect(screen.getByText('123 Main St')).toBeInTheDocument();
    expect(screen.getByText('$500,000')).toBeInTheDocument();
    expect(screen.getByText('2,000 sq ft')).toBeInTheDocument();
  });

  it('switches between tabs', async () => {
    const user = setupUser();

    renderWithProviders(
      <PropertyDrawer
        propertyId={mockProperty.id}
        isOpen={true}
        onClose={() => {}}
      />
    );

    // Click on Provenance tab
    const provenanceTab = screen.getByRole('tab', { name: /provenance/i });
    await user.click(provenanceTab);

    expect(screen.getByText(/data sources/i)).toBeInTheDocument();
  });

  it('displays scorecard with grade', () => {
    renderWithProviders(
      <PropertyDrawer
        propertyId={mockProperty.id}
        isOpen={true}
        onClose={() => {}}
      />
    );

    expect(screen.getByText('B+')).toBeInTheDocument();
    expect(screen.getByText('82%')).toBeInTheDocument();
  });

  it('closes drawer when close button clicked', async () => {
    const user = setupUser();
    const onClose = vi.fn();

    renderWithProviders(
      <PropertyDrawer
        propertyId={mockProperty.id}
        isOpen={true}
        onClose={onClose}
      />
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('does not render when closed', () => {
    const { container } = renderWithProviders(
      <PropertyDrawer
        propertyId={mockProperty.id}
        isOpen={false}
        onClose={() => {}}
      />
    );

    expect(container.firstChild).toBeNull();
  });
});
