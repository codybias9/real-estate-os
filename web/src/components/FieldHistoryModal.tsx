/**
 * FieldHistoryModal - Display version history for a specific field
 * Shows complete provenance timeline with value changes
 */

import React from 'react';
import { X, Clock, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useFieldHistory } from '@/hooks/useProperty';
import {
  formatFieldValue,
  formatDateTime,
  formatConfidence,
  getMethodColor,
  capitalize,
} from '@/utils/format';
import { cn } from '@/utils/cn';

interface FieldHistoryModalProps {
  propertyId: string;
  fieldPath: string;
  fieldLabel: string;
  onClose: () => void;
}

export function FieldHistoryModal({
  propertyId,
  fieldPath,
  fieldLabel,
  onClose,
}: FieldHistoryModalProps) {
  const { data: history, isLoading, error } = useFieldHistory(propertyId, fieldPath, true);

  // Calculate value changes
  const historyWithChanges = React.useMemo(() => {
    if (!history?.history) return [];

    return history.history.map((entry, idx) => {
      const prevEntry = history.history[idx + 1];
      let change: 'increase' | 'decrease' | 'same' | null = null;
      let changeAmount: number | null = null;

      if (prevEntry && typeof entry.value === 'number' && typeof prevEntry.value === 'number') {
        const diff = entry.value - prevEntry.value;
        if (diff > 0) {
          change = 'increase';
          changeAmount = diff;
        } else if (diff < 0) {
          change = 'decrease';
          changeAmount = Math.abs(diff);
        } else {
          change = 'same';
        }
      }

      return {
        ...entry,
        change,
        changeAmount,
      };
    });
  }, [history]);

  return (
    <div className="fixed inset-0 z-[60] overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="relative w-full max-w-3xl animate-fade-in">
          <div className="flex max-h-[80vh] flex-col rounded-lg bg-white shadow-2xl">
            {/* Header */}
            <div className="border-b border-gray-200 bg-gray-50 px-6 py-4">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">{fieldLabel} History</h2>
                  <p className="mt-1 text-sm text-gray-500">
                    Field path: <code className="rounded bg-gray-100 px-1 py-0.5">{fieldPath}</code>
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="ml-4 rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <span className="sr-only">Close</span>
                  <X className="h-6 w-6" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {isLoading ? (
                <div className="flex h-64 items-center justify-center">
                  <div className="text-center">
                    <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600 mx-auto" />
                    <p className="mt-4 text-sm text-gray-500">Loading history...</p>
                  </div>
                </div>
              ) : error ? (
                <div className="flex h-64 items-center justify-center">
                  <div className="text-center">
                    <p className="text-red-600">Failed to load history</p>
                    <p className="mt-2 text-sm text-gray-500">
                      {error instanceof Error ? error.message : 'Unknown error'}
                    </p>
                  </div>
                </div>
              ) : history && historyWithChanges.length > 0 ? (
                <div className="space-y-1">
                  {/* Summary */}
                  <div className="mb-6 rounded-lg bg-primary-50 p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-primary-900">
                        Total Versions: {history.total_versions}
                      </span>
                      <span className="text-sm text-primary-700">
                        Latest: {formatDateTime(historyWithChanges[0].extracted_at)}
                      </span>
                    </div>
                  </div>

                  {/* Timeline */}
                  <div className="relative">
                    {/* Vertical line */}
                    <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gray-200" />

                    {/* Version entries */}
                    <div className="space-y-6">
                      {historyWithChanges.map((entry, idx) => {
                        const confidence = formatConfidence(entry.confidence);
                        const isLatest = idx === 0;

                        return (
                          <div key={entry.id} className="relative pl-16">
                            {/* Timeline dot */}
                            <div
                              className={cn(
                                'absolute left-6 top-2 h-5 w-5 rounded-full border-4 border-white',
                                isLatest
                                  ? 'bg-primary-600 ring-4 ring-primary-100'
                                  : 'bg-gray-300'
                              )}
                            />

                            {/* Version card */}
                            <div
                              className={cn(
                                'rounded-lg border p-4',
                                isLatest
                                  ? 'border-primary-200 bg-primary-50'
                                  : 'border-gray-200 bg-white'
                              )}
                            >
                              {/* Header */}
                              <div className="flex items-start justify-between">
                                <div className="flex items-center gap-2">
                                  <span
                                    className={cn(
                                      'text-sm font-semibold',
                                      isLatest ? 'text-primary-900' : 'text-gray-900'
                                    )}
                                  >
                                    Version {entry.version}
                                  </span>
                                  {isLatest && (
                                    <span className="rounded-full bg-primary-600 px-2 py-0.5 text-xs font-medium text-white">
                                      Latest
                                    </span>
                                  )}
                                  {entry.method && (
                                    <span
                                      className={cn(
                                        'rounded-full px-2 py-0.5 text-xs font-medium',
                                        getMethodColor(entry.method)
                                      )}
                                    >
                                      {capitalize(entry.method)}
                                    </span>
                                  )}
                                </div>

                                {/* Change indicator */}
                                {entry.change && entry.change !== 'same' && entry.changeAmount && (
                                  <div
                                    className={cn(
                                      'flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium',
                                      entry.change === 'increase'
                                        ? 'bg-green-100 text-green-800'
                                        : 'bg-red-100 text-red-800'
                                    )}
                                  >
                                    {entry.change === 'increase' ? (
                                      <TrendingUp className="h-3 w-3" />
                                    ) : (
                                      <TrendingDown className="h-3 w-3" />
                                    )}
                                    <span>{formatFieldValue(fieldPath, entry.changeAmount)}</span>
                                  </div>
                                )}
                                {entry.change === 'same' && (
                                  <div className="flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700">
                                    <Minus className="h-3 w-3" />
                                    <span>No change</span>
                                  </div>
                                )}
                              </div>

                              {/* Value */}
                              <div className="mt-3">
                                <span className="text-sm text-gray-500">Value: </span>
                                <span className="text-lg font-semibold text-gray-900">
                                  {formatFieldValue(fieldPath, entry.value)}
                                </span>
                              </div>

                              {/* Metadata */}
                              <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                                <div>
                                  <span className="text-gray-500">Source: </span>
                                  <span className="font-medium text-gray-900">
                                    {entry.source_system || 'Unknown'}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-gray-500">Confidence: </span>
                                  <span className={cn('font-medium', confidence.color)}>
                                    {confidence.text}
                                  </span>
                                </div>
                                <div className="col-span-2 flex items-center gap-1">
                                  <Clock className="h-3 w-3 text-gray-400" />
                                  <span className="text-gray-500">
                                    {formatDateTime(entry.extracted_at)}
                                  </span>
                                </div>
                                {entry.source_url && (
                                  <div className="col-span-2">
                                    <span className="text-gray-500">URL: </span>
                                    <a
                                      href={entry.source_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-primary-600 hover:text-primary-700 hover:underline text-xs break-all"
                                    >
                                      {entry.source_url}
                                    </a>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex h-64 items-center justify-center">
                  <p className="text-gray-500">No history available for this field</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
