/**
 * ProvenanceTab - Display field-level provenance with history modals
 * Core component for Wave 1.6 - Deal Genome visualization
 */

import React, { useState } from 'react';
import {
  Info,
  Clock,
  AlertTriangle,
  TrendingUp,
  Database,
  Search,
} from 'lucide-react';
import type { PropertyDetail, FieldProvenanceBase } from '@/types/provenance';
import { useProvenanceStats } from '@/hooks/useProperty';
import {
  formatFieldValue,
  fieldPathToLabel,
  formatConfidence,
  getMethodColor,
  formatRelativeTime,
  isStale,
  capitalize,
} from '@/utils/format';
import { cn } from '@/utils/cn';
import { FieldHistoryModal } from './FieldHistoryModal';

interface ProvenanceTabProps {
  propertyId: string;
  property: PropertyDetail;
}

export function ProvenanceTab({ propertyId, property }: ProvenanceTabProps) {
  const { data: stats } = useProvenanceStats(propertyId);
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Get all fields with provenance
  const fieldsWithProvenance = Object.entries(property.fields)
    .map(([fieldPath, value]) => ({
      path: fieldPath,
      label: fieldPathToLabel(fieldPath),
      value,
      provenance: property.provenance[fieldPath],
    }))
    .filter((field) => field.provenance) // Only show fields with provenance
    .filter((field) =>
      searchTerm
        ? field.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
          field.path.toLowerCase().includes(searchTerm.toLowerCase())
        : true
    )
    .sort((a, b) => a.label.localeCompare(b.label));

  return (
    <div className="p-6 space-y-6">
      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-600" />
              <span className="text-sm font-medium text-gray-600">Total Fields</span>
            </div>
            <p className="mt-2 text-3xl font-bold text-gray-900">{stats.total_fields}</p>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              <span className="text-sm font-medium text-gray-600">Coverage</span>
            </div>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {Math.round(stats.coverage_percentage)}%
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center gap-2">
              <Info className="h-5 w-5 text-purple-600" />
              <span className="text-sm font-medium text-gray-600">Avg Confidence</span>
            </div>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {Math.round(stats.avg_confidence * 100)}%
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
              <span className="text-sm font-medium text-gray-600">Stale Fields</span>
            </div>
            <p className="mt-2 text-3xl font-bold text-gray-900">{stats.stale_fields}</p>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search fields..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
      </div>

      {/* Fields Table */}
      <div className="overflow-hidden rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Field
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Value
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Source
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Confidence
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {fieldsWithProvenance.map((field) => {
              const confidence = formatConfidence(field.provenance?.confidence);
              const stale = isStale(field.provenance?.extracted_at);

              return (
                <tr
                  key={field.path}
                  className={cn(
                    'hover:bg-gray-50 transition-colors',
                    stale && 'bg-orange-50'
                  )}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{field.label}</span>
                      {stale && (
                        <AlertTriangle
                          className="h-4 w-4 text-orange-500"
                          title="Data is stale (>30 days)"
                        />
                      )}
                    </div>
                    <span className="text-xs text-gray-500">{field.path}</span>
                  </td>

                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-900">
                      {formatFieldValue(field.path, field.value)}
                    </span>
                  </td>

                  <td className="px-6 py-4">
                    {field.provenance && (
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900">
                            {field.provenance.source_system || 'Unknown'}
                          </span>
                          {field.provenance.method && (
                            <span
                              className={cn(
                                'rounded-full px-2 py-0.5 text-xs font-medium',
                                getMethodColor(field.provenance.method)
                              )}
                            >
                              {capitalize(field.provenance.method)}
                            </span>
                          )}
                        </div>
                        {field.provenance.extracted_at && (
                          <div className="flex items-center gap-1 text-xs text-gray-500">
                            <Clock className="h-3 w-3" />
                            <span>{formatRelativeTime(field.provenance.extracted_at)}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </td>

                  <td className="px-6 py-4">
                    {field.provenance && (
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200">
                          <div
                            className={cn(
                              'h-full transition-all',
                              field.provenance.confidence && field.provenance.confidence >= 0.9
                                ? 'bg-green-600'
                                : field.provenance.confidence && field.provenance.confidence >= 0.75
                                ? 'bg-blue-600'
                                : field.provenance.confidence && field.provenance.confidence >= 0.5
                                ? 'bg-yellow-600'
                                : 'bg-red-600'
                            )}
                            style={{
                              width: `${(field.provenance.confidence || 0) * 100}%`,
                            }}
                          />
                        </div>
                        <span className={cn('text-sm font-medium', confidence.color)}>
                          {confidence.text}
                        </span>
                      </div>
                    )}
                  </td>

                  <td className="px-6 py-4">
                    <button
                      onClick={() => setSelectedField(field.path)}
                      className="flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700"
                    >
                      <Clock className="h-4 w-4" />
                      History
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {fieldsWithProvenance.length === 0 && (
          <div className="py-12 text-center">
            <Database className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-4 text-sm text-gray-500">
              {searchTerm ? 'No fields match your search' : 'No provenance data available'}
            </p>
          </div>
        )}
      </div>

      {/* Source Distribution */}
      {stats && Object.keys(stats.by_source_system).length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Data Sources</h3>
          <div className="space-y-3">
            {Object.entries(stats.by_source_system)
              .sort(([, a], [, b]) => b - a)
              .map(([source, count]) => {
                const percentage = (count / stats.total_fields) * 100;
                return (
                  <div key={source}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">{source}</span>
                      <span className="text-sm text-gray-500">
                        {count} fields ({Math.round(percentage)}%)
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                      <div
                        className="h-full bg-primary-600 transition-all"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Field History Modal */}
      {selectedField && (
        <FieldHistoryModal
          propertyId={propertyId}
          fieldPath={selectedField}
          fieldLabel={fieldPathToLabel(selectedField)}
          onClose={() => setSelectedField(null)}
        />
      )}
    </div>
  );
}
