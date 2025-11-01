/**
 * DetailsTab - Display basic property details
 */

import React from 'react';
import { Home, MapPin, Users, FileText } from 'lucide-react';
import type { PropertyDetail } from '@/types/provenance';
import { formatFieldValue, fieldPathToLabel } from '@/utils/format';

interface DetailsTabProps {
  property: PropertyDetail;
}

interface Section {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  fields: string[];
}

export function DetailsTab({ property }: DetailsTabProps) {
  const sections: Section[] = [
    {
      title: 'Property Information',
      icon: Home,
      fields: [
        'property_type',
        'bedrooms',
        'bathrooms',
        'square_footage',
        'lot_size_sqft',
        'year_built',
        'parking_spaces',
        'garage_spaces',
      ],
    },
    {
      title: 'Financial',
      icon: FileText,
      fields: [
        'listing_price',
        'estimated_value',
        'tax_assessed_value',
        'annual_tax_amount',
        'hoa_fee',
        'price_per_sqft',
      ],
    },
    {
      title: 'Location',
      icon: MapPin,
      fields: ['county', 'parcel'],
    },
  ];

  return (
    <div className="p-6 space-y-8">
      {/* Address */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-6">
        <div className="flex items-start gap-4">
          <MapPin className="h-6 w-6 text-primary-600 flex-shrink-0 mt-1" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Address</h3>
            <p className="mt-2 text-gray-700">
              {property.canonical_address.street || 'Unknown Street'}
              <br />
              {[
                property.canonical_address.city,
                property.canonical_address.state,
                property.canonical_address.zip,
              ]
                .filter(Boolean)
                .join(', ')}
            </p>
            {(property.lat || property.lon) && (
              <p className="mt-2 text-sm text-gray-500">
                Coordinates: {property.lat?.toFixed(6)}, {property.lon?.toFixed(6)}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Dynamic sections */}
      {sections.map((section) => {
        const sectionFields = section.fields
          .map((fieldPath) => ({
            path: fieldPath,
            label: fieldPathToLabel(fieldPath),
            value: property.fields[fieldPath],
          }))
          .filter((field) => field.value !== undefined && field.value !== null);

        if (sectionFields.length === 0) return null;

        return (
          <div key={section.title} className="space-y-4">
            <div className="flex items-center gap-2">
              <section.icon className="h-5 w-5 text-gray-400" />
              <h3 className="text-lg font-semibold text-gray-900">{section.title}</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {sectionFields.map((field) => (
                <div key={field.path} className="space-y-1">
                  <dt className="text-sm font-medium text-gray-500">{field.label}</dt>
                  <dd className="text-base text-gray-900">
                    {formatFieldValue(field.path, field.value)}
                  </dd>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {/* Owners */}
      {property.owners && property.owners.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900">Owners</h3>
          </div>
          <div className="space-y-3">
            {property.owners.map((link, idx) => (
              <div key={idx} className="rounded-lg border border-gray-200 p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{link.owner.canonical_name}</p>
                    {link.owner.entity_type && (
                      <p className="mt-1 text-sm text-gray-500">
                        Type: {link.owner.entity_type}
                      </p>
                    )}
                    {link.role && (
                      <p className="text-sm text-gray-500">Role: {link.role}</p>
                    )}
                  </div>
                  {link.share_pct !== null && link.share_pct !== undefined && (
                    <span className="rounded-full bg-primary-100 px-3 py-1 text-sm font-medium text-primary-800">
                      {link.share_pct}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Deals */}
      {property.deals && property.deals.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900">Deals</h3>
          </div>
          <div className="space-y-3">
            {property.deals.map((deal) => (
              <div key={deal.id} className="rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">Stage: {deal.stage}</p>
                    {deal.probability && (
                      <p className="mt-1 text-sm text-gray-500">
                        Probability: {Math.round(deal.probability * 100)}%
                      </p>
                    )}
                    {deal.expected_close_date && (
                      <p className="text-sm text-gray-500">
                        Expected close: {new Date(deal.expected_close_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Description */}
      {property.fields.description && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Description</h3>
          <p className="text-gray-700 leading-relaxed">{property.fields.description}</p>
        </div>
      )}
    </div>
  );
}
