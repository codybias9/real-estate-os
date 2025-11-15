'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { propertiesApi } from '@/lib/api';
import { Property } from '@/types';

export default function PropertiesPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: '',
    city: '',
    status: '',
    min_price: '',
    max_price: '',
  });

  useEffect(() => {
    loadProperties();
  }, [filters]);

  const loadProperties = async () => {
    try {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v !== '')
      );
      const response = await propertiesApi.list(params);
      setProperties(response.data.properties || []);
    } catch (error) {
      console.error('Error loading properties:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, string> = {
      new: 'badge-info',
      enriched: 'badge-warning',
      scored: 'badge-success',
      documented: 'badge-success',
    };
    return badges[status] || 'badge-info';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="md:flex md:items-center md:justify-between mb-6">
        <div className="flex-1 min-w-0">
          <h1 className="text-3xl font-bold text-gray-900">Properties</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage and analyze investment properties
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="Search address, city..."
            className="input"
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
          <select
            className="input"
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="enriched">Enriched</option>
            <option value="scored">Scored</option>
            <option value="documented">Documented</option>
          </select>
          <input
            type="number"
            placeholder="Min Price"
            className="input"
            value={filters.min_price}
            onChange={(e) => setFilters({ ...filters, min_price: e.target.value })}
          />
          <input
            type="number"
            placeholder="Max Price"
            className="input"
            value={filters.max_price}
            onChange={(e) => setFilters({ ...filters, max_price: e.target.value })}
          />
        </div>
      </div>

      {/* Properties List */}
      {loading ? (
        <div className="text-center py-12">Loading properties...</div>
      ) : properties.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">No properties found. Try adjusting your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {properties.map((property) => (
            <Link key={property.id} href={`/properties/${property.id}`}>
              <div className="card hover:shadow-md transition-shadow cursor-pointer">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {property.address}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {property.city}, {property.state} {property.zip_code}
                    </p>
                  </div>
                  <span className={`badge ${getStatusBadge(property.status)} ml-2`}>
                    {property.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <p className="text-2xl font-bold text-gray-900">
                      ${property.price.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">Listing Price</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-700">
                      {property.bedrooms || '-'} bed • {property.bathrooms || '-'} bath
                    </p>
                    <p className="text-xs text-gray-500">
                      {property.sqft ? `${property.sqft.toLocaleString()} sqft` : 'Size TBD'}
                    </p>
                  </div>
                </div>

                {property.description && (
                  <p className="mt-3 text-sm text-gray-600 line-clamp-2">
                    {property.description}
                  </p>
                )}

                <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
                  <span>{property.property_type.replace('_', ' ')}</span>
                  <span>{new Date(property.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
