/**
 * Property filter panel
 */

import { PropertyState } from '@/types';
import type { PropertyFilters as Filters } from '@/lib/api-client';

interface PropertyFiltersProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

export function PropertyFilters({ filters, onChange }: PropertyFiltersProps) {
  const states = Object.values(PropertyState);

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Search */}
        <div>
          <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
            Search
          </label>
          <input
            type="text"
            id="search"
            placeholder="Address or APN..."
            value={filters.search || ''}
            onChange={(e) => onChange({ ...filters, search: e.target.value || undefined })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* State filter */}
        <div>
          <label htmlFor="state" className="block text-sm font-medium text-gray-700 mb-1">
            State
          </label>
          <select
            id="state"
            value={filters.state?.[0] || ''}
            onChange={(e) =>
              onChange({
                ...filters,
                state: e.target.value ? [e.target.value as PropertyState] : undefined,
              })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All states</option>
            {states.map((state) => (
              <option key={state} value={state}>
                {state.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>

        {/* Min score */}
        <div>
          <label htmlFor="min_score" className="block text-sm font-medium text-gray-700 mb-1">
            Min Score
          </label>
          <input
            type="number"
            id="min_score"
            placeholder="0"
            min="0"
            max="100"
            value={filters.min_score || ''}
            onChange={(e) =>
              onChange({
                ...filters,
                min_score: e.target.value ? parseInt(e.target.value) : undefined,
              })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Max score */}
        <div>
          <label htmlFor="max_score" className="block text-sm font-medium text-gray-700 mb-1">
            Max Score
          </label>
          <input
            type="number"
            id="max_score"
            placeholder="100"
            min="0"
            max="100"
            value={filters.max_score || ''}
            onChange={(e) =>
              onChange({
                ...filters,
                max_score: e.target.value ? parseInt(e.target.value) : undefined,
              })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* Clear filters */}
      {(filters.search || filters.state || filters.min_score || filters.max_score) && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={() =>
              onChange({
                page: 1,
                per_page: filters.per_page,
              })
            }
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
}
