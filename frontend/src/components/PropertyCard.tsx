/**
 * Property card component for list view
 */

import type { Property } from '@/types';
import { formatNumber, getStateBadgeColor, getScoreBadgeColor } from '@/lib/utils';

interface PropertyCardProps {
  property: Property;
  onClick: () => void;
}

export function PropertyCard({ property, onClick }: PropertyCardProps) {
  const address = [property.street, property.city, property.state, property.zip]
    .filter(Boolean)
    .join(', ');

  return (
    <div
      onClick={onClick}
      className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-3">
            <h3 className="text-lg font-medium text-gray-900 truncate">{address || 'Unknown Address'}</h3>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStateBadgeColor(
                property.state
              )}`}
            >
              {property.state.replace('_', ' ')}
            </span>
          </div>

          <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500">
            <span>APN: {property.apn}</span>
            {property.county && <span>• {property.county}</span>}
            {property.beds && property.baths && (
              <span>
                • {property.beds} bed, {property.baths} bath
              </span>
            )}
            {property.sqft && <span>• {formatNumber(property.sqft)} sqft</span>}
          </div>

          {property.owner && (
            <div className="mt-1 text-sm text-gray-500">
              Owner: {property.owner.name || 'Unknown'} ({property.owner.type || 'Unknown'})
            </div>
          )}
        </div>

        {property.score !== undefined && (
          <div className="ml-4 flex-shrink-0">
            <div className="flex items-center">
              <div
                className={`w-16 h-16 rounded-full ${getScoreBadgeColor(
                  property.score
                )} flex items-center justify-center`}
              >
                <span className="text-2xl font-bold text-white">{property.score}</span>
              </div>
              <div className="ml-3">
                <div className="text-sm font-medium text-gray-900">Investment Score</div>
                <div className="text-xs text-gray-500">
                  {property.score >= 80
                    ? 'Excellent'
                    : property.score >= 60
                      ? 'Good'
                      : property.score >= 40
                        ? 'Fair'
                        : 'Poor'}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
