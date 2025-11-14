/**
 * Tests for PropertyCard component
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { PropertyCard } from '@/components/PropertyCard';
import { PropertyState } from '@/types';

describe('PropertyCard', () => {
  const mockProperty = {
    id: '123',
    tenant_id: 'tenant-1',
    apn: '203-656-44',
    apn_hash: 'abc123',
    street: '123 Main St',
    city: 'Las Vegas',
    state: 'NV',
    zip: '89101',
    county: 'Clark',
    beds: 3,
    baths: 2,
    sqft: 1800,
    lot_sqft: 6500,
    year_built: 2010,
    state: PropertyState.SCORED,
    state_updated_at: '2025-11-02T12:00:00Z',
    score: 78,
    created_at: '2025-11-01T10:00:00Z',
    updated_at: '2025-11-02T12:00:00Z',
    owner: {
      name: 'John Doe',
      type: 'Person' as const,
    },
  };

  const mockOnClick = jest.fn();

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders property address', () => {
    render(<PropertyCard property={mockProperty} onClick={mockOnClick} />);

    expect(screen.getByText(/123 Main St, Las Vegas, NV, 89101/i)).toBeInTheDocument();
  });

  it('renders APN and property details', () => {
    render(<PropertyCard property={mockProperty} onClick={mockOnClick} />);

    expect(screen.getByText(/APN: 203-656-44/i)).toBeInTheDocument();
    expect(screen.getByText(/Clark/i)).toBeInTheDocument();
    expect(screen.getByText(/3 bed, 2 bath/i)).toBeInTheDocument();
    expect(screen.getByText(/1,800 sqft/i)).toBeInTheDocument();
  });

  it('renders owner information', () => {
    render(<PropertyCard property={mockProperty} onClick={mockOnClick} />);

    expect(screen.getByText(/Owner: John Doe \(Person\)/i)).toBeInTheDocument();
  });

  it('renders score badge when score exists', () => {
    render(<PropertyCard property={mockProperty} onClick={mockOnClick} />);

    expect(screen.getByText('78')).toBeInTheDocument();
    expect(screen.getByText(/Investment Score/i)).toBeInTheDocument();
    expect(screen.getByText(/Good/i)).toBeInTheDocument();
  });

  it('does not render score badge when score is undefined', () => {
    const propertyWithoutScore = { ...mockProperty, score: undefined };
    render(<PropertyCard property={propertyWithoutScore} onClick={mockOnClick} />);

    expect(screen.queryByText(/Investment Score/i)).not.toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    render(<PropertyCard property={mockProperty} onClick={mockOnClick} />);

    const card = screen.getByText(/123 Main St/i).closest('div');
    fireEvent.click(card!);

    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it('renders state badge with correct styling', () => {
    render(<PropertyCard property={mockProperty} onClick={mockOnClick} />);

    const stateBadge = screen.getByText(/scored/i);
    expect(stateBadge).toHaveClass('bg-purple-100', 'text-purple-800');
  });

  it('handles missing optional fields gracefully', () => {
    const minimalProperty = {
      ...mockProperty,
      street: undefined,
      city: undefined,
      state: undefined,
      zip: undefined,
      county: undefined,
      beds: undefined,
      baths: undefined,
      sqft: undefined,
      owner: undefined,
    };

    render(<PropertyCard property={minimalProperty} onClick={mockOnClick} />);

    expect(screen.getByText(/Unknown Address/i)).toBeInTheDocument();
    expect(screen.getByText(/APN: 203-656-44/i)).toBeInTheDocument();
  });
});
