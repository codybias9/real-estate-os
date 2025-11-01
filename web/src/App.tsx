/**
 * Main App Component
 * Demo application showcasing PropertyDrawer with Deal Genome provenance
 */

import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PropertyDrawer } from './components/PropertyDrawer';
import { Database } from 'lucide-react';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(null);
  const [demoPropertyId, setDemoPropertyId] = useState('');

  // Demo property IDs for testing
  const demoProperties = [
    { id: '123e4567-e89b-12d3-a456-426614174000', label: 'Sample Property 1' },
    { id: '223e4567-e89b-12d3-a456-426614174001', label: 'Sample Property 2' },
  ];

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="text-center">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-primary-600 shadow-lg">
              <Database className="h-10 w-10 text-white" />
            </div>
            <h1 className="mt-6 text-4xl font-bold tracking-tight text-gray-900">
              Real Estate OS - Deal Genome
            </h1>
            <p className="mt-4 text-lg text-gray-600">
              Field-level provenance tracking for complete data lineage
            </p>
          </div>

          {/* Demo Controls */}
          <div className="mt-12 rounded-2xl bg-white p-8 shadow-xl">
            <h2 className="text-2xl font-bold text-gray-900">Property Drawer Demo</h2>
            <p className="mt-2 text-gray-600">
              Open the property drawer to explore provenance tracking, scorecard explainability,
              and field history.
            </p>

            {/* Quick access buttons */}
            <div className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quick Access
                </label>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {demoProperties.map((prop) => (
                    <button
                      key={prop.id}
                      onClick={() => setSelectedPropertyId(prop.id)}
                      className="flex items-center justify-between rounded-lg border border-gray-300 bg-white px-4 py-3 text-left hover:border-primary-500 hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <span className="font-medium text-gray-900">{prop.label}</span>
                      <svg
                        className="h-5 w-5 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </button>
                  ))}
                </div>
              </div>

              {/* Manual entry */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Or Enter Property ID
                </label>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={demoPropertyId}
                    onChange={(e) => setDemoPropertyId(e.target.value)}
                    placeholder="e.g., 123e4567-e89b-12d3-a456-426614174000"
                    className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                  <button
                    onClick={() => demoPropertyId && setSelectedPropertyId(demoPropertyId)}
                    disabled={!demoPropertyId}
                    className="rounded-lg bg-primary-600 px-6 py-2 font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Open
                  </button>
                </div>
              </div>
            </div>

            {/* Features list */}
            <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg bg-blue-50 p-4">
                <h3 className="font-semibold text-blue-900">Provenance Tab</h3>
                <p className="mt-1 text-sm text-blue-700">
                  View source, method, and confidence for every field
                </p>
              </div>
              <div className="rounded-lg bg-green-50 p-4">
                <h3 className="font-semibold text-green-900">Field History</h3>
                <p className="mt-1 text-sm text-green-700">
                  See complete version timeline with value changes
                </p>
              </div>
              <div className="rounded-lg bg-purple-50 p-4">
                <h3 className="font-semibold text-purple-900">Scorecard</h3>
                <p className="mt-1 text-sm text-purple-700">
                  ML explainability with SHAP values and drivers
                </p>
              </div>
              <div className="rounded-lg bg-orange-50 p-4">
                <h3 className="font-semibold text-orange-900">Stale Detection</h3>
                <p className="mt-1 text-sm text-orange-700">
                  Automatic alerts for outdated data (&gt;30 days)
                </p>
              </div>
            </div>
          </div>

          {/* API Configuration */}
          <div className="mt-8 rounded-lg bg-yellow-50 p-4 border border-yellow-200">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800">Configuration Required</h3>
                <div className="mt-2 text-sm text-yellow-700">
                  <p>
                    Make sure your FastAPI backend is running on port 8000. Set environment
                    variables:
                  </p>
                  <ul className="mt-2 list-disc list-inside space-y-1">
                    <li>
                      <code className="bg-yellow-100 px-1 py-0.5 rounded">
                        VITE_API_BASE_URL
                      </code>{' '}
                      - API base URL (default: /api)
                    </li>
                    <li>
                      <code className="bg-yellow-100 px-1 py-0.5 rounded">
                        VITE_TENANT_ID
                      </code>{' '}
                      - Your tenant UUID
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Property Drawer */}
        {selectedPropertyId && (
          <PropertyDrawer
            propertyId={selectedPropertyId}
            onClose={() => setSelectedPropertyId(null)}
          />
        )}
      </div>
    </QueryClientProvider>
  );
}

export default App;
