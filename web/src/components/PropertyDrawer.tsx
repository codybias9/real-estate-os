/**
 * PropertyDrawer - Main drawer component with tabbed interface
 * Displays property details, provenance, scorecard, timeline, similar properties, and comp analysis
 * Wave 2.4: Added ML-powered similar properties tab
 * Wave 3.1: Added comp analysis tab
 */

import React, { useState } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/utils/cn';
import { useProperty } from '@/hooks/useProperty';
import { DetailsTab } from './DetailsTab';
import { ProvenanceTab } from './ProvenanceTab';
import { ScorecardTab } from './ScorecardTab';
import { TimelineTab } from './TimelineTab';
import { SimilarPropertiesTab } from './SimilarPropertiesTab';
import { CompAnalysisTab } from './CompAnalysisTab';
import { NegotiationTab } from './NegotiationTab';

interface PropertyDrawerProps {
  propertyId: string;
  onClose: () => void;
}

type TabId = 'details' | 'provenance' | 'scorecard' | 'timeline' | 'similar' | 'comps' | 'negotiate';

interface Tab {
  id: TabId;
  label: string;
  badge?: string | number;
}

export function PropertyDrawer({ propertyId, onClose }: PropertyDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('details');
  const { data: property, isLoading, error } = useProperty(propertyId);

  const tabs: Tab[] = [
    { id: 'details', label: 'Details' },
    { id: 'provenance', label: 'Provenance', badge: property?.fields ? Object.keys(property.fields).length : undefined },
    { id: 'scorecard', label: 'Scorecard' },
    { id: 'comps', label: 'Comps', badge: '📊' },
    { id: 'negotiate', label: 'Negotiate', badge: '🎯' },
    { id: 'similar', label: 'Similar', badge: '✨' },
    { id: 'timeline', label: 'Timeline' },
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="absolute inset-y-0 right-0 flex max-w-full pl-10">
        <div className="relative w-screen max-w-4xl animate-slide-in">
          <div className="flex h-full flex-col bg-white shadow-xl">
            {/* Header */}
            <div className="border-b border-gray-200 bg-gray-50 px-6 py-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  {isLoading ? (
                    <div className="h-8 w-64 animate-pulse rounded bg-gray-200" />
                  ) : error ? (
                    <h2 className="text-xl font-semibold text-red-600">Error loading property</h2>
                  ) : property ? (
                    <>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {property.canonical_address.street || 'Unknown Address'}
                      </h2>
                      <p className="mt-1 text-sm text-gray-500">
                        {[
                          property.canonical_address.city,
                          property.canonical_address.state,
                          property.canonical_address.zip,
                        ]
                          .filter(Boolean)
                          .join(', ')}
                      </p>
                    </>
                  ) : null}
                </div>
                <button
                  onClick={onClose}
                  className="ml-4 rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <span className="sr-only">Close</span>
                  <X className="h-6 w-6" />
                </button>
              </div>

              {/* Tabs */}
              <div className="mt-4 flex space-x-1 border-b border-gray-200">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      'flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors',
                      activeTab === tab.id
                        ? 'border-primary-500 text-primary-600'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    )}
                  >
                    {tab.label}
                    {tab.badge !== undefined && (
                      <span
                        className={cn(
                          'rounded-full px-2 py-0.5 text-xs font-medium',
                          activeTab === tab.id
                            ? 'bg-primary-100 text-primary-700'
                            : 'bg-gray-100 text-gray-600'
                        )}
                      >
                        {tab.badge}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {isLoading ? (
                <div className="flex h-full items-center justify-center">
                  <div className="text-center">
                    <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600 mx-auto" />
                    <p className="mt-4 text-sm text-gray-500">Loading property data...</p>
                  </div>
                </div>
              ) : error ? (
                <div className="flex h-full items-center justify-center">
                  <div className="text-center">
                    <p className="text-red-600">Failed to load property</p>
                    <p className="mt-2 text-sm text-gray-500">
                      {error instanceof Error ? error.message : 'Unknown error'}
                    </p>
                  </div>
                </div>
              ) : property ? (
                <>
                  {activeTab === 'details' && <DetailsTab property={property} />}
                  {activeTab === 'provenance' && <ProvenanceTab propertyId={propertyId} property={property} />}
                  {activeTab === 'scorecard' && <ScorecardTab propertyId={propertyId} />}
                  {activeTab === 'comps' && <CompAnalysisTab propertyId={propertyId} property={property} />}
                  {activeTab === 'negotiate' && <NegotiationTab propertyId={propertyId} property={property} />}
                  {activeTab === 'similar' && <SimilarPropertiesTab propertyId={propertyId} property={property} />}
                  {activeTab === 'timeline' && <TimelineTab propertyId={propertyId} />}
                </>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
