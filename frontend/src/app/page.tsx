'use client';

/**
 * Home page - Property dashboard
 */

import { useState } from 'react';
import { PropertyList } from '@/components/PropertyList';
import { PropertyDrawer } from '@/components/PropertyDrawer';
import { Header } from '@/components/Header';

export default function HomePage() {
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | undefined>();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handlePropertySelect = (propertyId: string) => {
    setSelectedPropertyId(propertyId);
    setDrawerOpen(true);
  };

  const handleDrawerClose = () => {
    setDrawerOpen(false);
    // Clear selection after animation completes
    setTimeout(() => setSelectedPropertyId(undefined), 300);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Properties</h1>
          <p className="mt-2 text-gray-600">
            Discover, enrich, and score investment properties
          </p>
        </div>

        <PropertyList onPropertySelect={handlePropertySelect} />
      </main>

      <PropertyDrawer
        propertyId={selectedPropertyId}
        open={drawerOpen}
        onClose={handleDrawerClose}
      />
    </div>
  );
}
