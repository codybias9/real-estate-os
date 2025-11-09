'use client';

/**
 * Property list with filtering and pagination
 */

import { useState } from 'react';
import { useProperties } from '@/hooks';
import { PropertyCard } from './PropertyCard';
import { PropertyFilters } from './PropertyFilters';
import { LoadingSpinner } from './LoadingSpinner';
import type { PropertyFilters as Filters } from '@/lib/api-client';

interface PropertyListProps {
  onPropertySelect: (propertyId: string) => void;
}

export function PropertyList({ onPropertySelect }: PropertyListProps) {
  const [filters, setFilters] = useState<Filters>({
    page: 1,
    per_page: 20,
  });

  const { data, isLoading, error } = useProperties(filters);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-medium">Error loading properties</h3>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : 'Unknown error occurred'}
        </p>
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-12 text-center">
        <div className="text-gray-400 mb-4">
          <svg
            className="mx-auto h-12 w-12"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No properties found</h3>
        <p className="text-gray-600">
          Try adjusting your filters or wait for properties to be discovered.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PropertyFilters filters={filters} onChange={setFilters} />

      <div className="bg-white rounded-lg shadow">
        <div className="px-4 py-3 border-b border-gray-200">
          <p className="text-sm text-gray-700">
            Showing <span className="font-medium">{data.items.length}</span> of{' '}
            <span className="font-medium">{data.total}</span> properties
          </p>
        </div>

        <div className="divide-y divide-gray-200">
          {data.items.map((property) => (
            <PropertyCard
              key={property.id}
              property={property}
              onClick={() => onPropertySelect(property.id)}
            />
          ))}
        </div>

        {data.pages > 1 && (
          <div className="px-4 py-3 border-t border-gray-200 flex justify-between items-center">
            <button
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) - 1 }))}
              disabled={filters.page === 1}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-gray-700">
              Page {filters.page} of {data.pages}
            </span>
            <button
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) + 1 }))}
              disabled={filters.page === data.pages}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
