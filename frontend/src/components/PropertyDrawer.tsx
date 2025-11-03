'use client';

/**
 * Property detail drawer with tabs for overview, score, timeline, outreach
 */

import { useState, useEffect } from 'react';
import { useProperty, usePropertyScore } from '@/hooks';
import { LoadingSpinner } from './LoadingSpinner';
import { ScoreVisualization } from './ScoreVisualization';
import { Timeline } from './Timeline';
import { formatNumber, formatDate, getStateBadgeColor } from '@/lib/utils';

interface PropertyDrawerProps {
  propertyId: string | undefined;
  open: boolean;
  onClose: () => void;
}

type Tab = 'overview' | 'score' | 'timeline' | 'outreach';

export function PropertyDrawer({ propertyId, open, onClose }: PropertyDrawerProps) {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const { data: property, isLoading } = useProperty(propertyId);
  const { data: scoreResult } = usePropertyScore(propertyId);

  // Reset tab when drawer opens
  useEffect(() => {
    if (open) {
      setActiveTab('overview');
    }
  }, [open]);

  if (!open) return null;

  const address = property
    ? [property.street, property.city, property.state, property.zip].filter(Boolean).join(', ')
    : '';

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 max-w-3xl w-full bg-white shadow-xl z-50 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              {isLoading ? (
                <div className="h-8 w-64 bg-gray-200 animate-pulse rounded" />
              ) : (
                <>
                  <h2 className="text-2xl font-bold text-gray-900 truncate">{address}</h2>
                  <div className="mt-1 flex items-center space-x-3">
                    <span className="text-sm text-gray-500">APN: {property?.apn}</span>
                    {property && (
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStateBadgeColor(
                          property.state
                        )}`}
                      >
                        {property.state.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>
            <button
              onClick={onClose}
              className="ml-4 text-gray-400 hover:text-gray-500 focus:outline-none"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Tabs */}
          <div className="mt-4 flex space-x-4 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('overview')}
              className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('score')}
              className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'score'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Score
            </button>
            <button
              onClick={() => setActiveTab('timeline')}
              className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'timeline'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Timeline
            </button>
            <button
              onClick={() => setActiveTab('outreach')}
              className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'outreach'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Outreach
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {isLoading ? (
            <div className="flex justify-center items-center h-full">
              <LoadingSpinner size="large" />
            </div>
          ) : !property ? (
            <div className="text-center text-gray-500">Property not found</div>
          ) : (
            <>
              {activeTab === 'overview' && <OverviewTab property={property} />}
              {activeTab === 'score' && (
                <ScoreVisualization
                  score={property.score}
                  scoreResult={scoreResult}
                  isLoading={!scoreResult}
                />
              )}
              {activeTab === 'timeline' && <Timeline propertyId={property.id} />}
              {activeTab === 'outreach' && <OutreachTab propertyId={property.id} />}
            </>
          )}
        </div>
      </div>
    </>
  );
}

function OverviewTab({ property }: { property: any }) {
  return (
    <div className="space-y-6">
      {/* Property Details */}
      <section>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Property Details</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Bedrooms</dt>
            <dd className="mt-1 text-sm text-gray-900">{property.beds || 'N/A'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Bathrooms</dt>
            <dd className="mt-1 text-sm text-gray-900">{property.baths || 'N/A'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Square Feet</dt>
            <dd className="mt-1 text-sm text-gray-900">{formatNumber(property.sqft)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Lot Size</dt>
            <dd className="mt-1 text-sm text-gray-900">{formatNumber(property.lot_sqft)} sqft</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Year Built</dt>
            <dd className="mt-1 text-sm text-gray-900">{property.year_built || 'N/A'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Stories</dt>
            <dd className="mt-1 text-sm text-gray-900">{property.stories || 'N/A'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Garage</dt>
            <dd className="mt-1 text-sm text-gray-900">
              {property.garage_spaces ? `${property.garage_spaces} spaces` : 'N/A'}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Pool</dt>
            <dd className="mt-1 text-sm text-gray-900">{property.pool ? 'Yes' : 'No'}</dd>
          </div>
        </div>
      </section>

      {/* Owner Information */}
      {property.owner && (
        <section>
          <h3 className="text-lg font-medium text-gray-900 mb-4">Owner Information</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">Name</dt>
              <dd className="mt-1 text-sm text-gray-900">{property.owner.name || 'N/A'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Type</dt>
              <dd className="mt-1 text-sm text-gray-900">{property.owner.type || 'N/A'}</dd>
            </div>
            {property.owner.email && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Email</dt>
                <dd className="mt-1 text-sm text-gray-900">{property.owner.email}</dd>
              </div>
            )}
            {property.owner.phone && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Phone</dt>
                <dd className="mt-1 text-sm text-gray-900">{property.owner.phone}</dd>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Timestamps */}
      <section>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Timestamps</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Discovered</dt>
            <dd className="mt-1 text-sm text-gray-900">{formatDate(property.created_at)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
            <dd className="mt-1 text-sm text-gray-900">{formatDate(property.updated_at)}</dd>
          </div>
        </div>
      </section>
    </div>
  );
}

function OutreachTab({ propertyId }: { propertyId: string }) {
  return (
    <div className="text-center text-gray-500 py-12">
      <p>Outreach campaigns will be displayed here</p>
      <p className="text-sm mt-2">Coming soon...</p>
    </div>
  );
}
