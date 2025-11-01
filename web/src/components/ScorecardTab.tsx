/**
 * ScorecardTab - Display ML scorecard with SHAP explainability
 * Shows score drivers, counterfactuals, and SHAP values
 */

import React from 'react';
import { TrendingUp, TrendingDown, Award, AlertCircle, Lightbulb } from 'lucide-react';
import { useScorecard } from '@/hooks/useProperty';
import { formatDateTime, capitalize } from '@/utils/format';
import { cn } from '@/utils/cn';

interface ScorecardTabProps {
  propertyId: string;
}

export function ScorecardTab({ propertyId }: ScorecardTabProps) {
  const { data: explainability, isLoading, error } = useScorecard(propertyId);

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600 mx-auto" />
          <p className="mt-4 text-sm text-gray-500">Loading scorecard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-gray-600">No scorecard available</p>
          <p className="mt-2 text-sm text-gray-500">
            This property hasn't been scored yet.
          </p>
        </div>
      </div>
    );
  }

  if (!explainability) {
    return null;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="rounded-lg border border-gray-200 bg-gradient-to-r from-primary-50 to-blue-50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="rounded-full bg-white p-3 shadow-md">
              <Award className="h-8 w-8 text-primary-600" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900">ML Score Analysis</h3>
              <p className="mt-1 text-sm text-gray-600">
                Generated {formatDateTime(explainability.created_at)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Top Positive Drivers */}
      {explainability.top_positive_drivers.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-green-600" />
            <h3 className="text-lg font-semibold text-gray-900">Top Positive Drivers</h3>
            <span className="text-sm text-gray-500">
              ({explainability.top_positive_drivers.length})
            </span>
          </div>
          <div className="space-y-3">
            {explainability.top_positive_drivers.map((driver, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-green-200 bg-green-50 p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-green-900">
                        {capitalize(driver.feature.replace(/_/g, ' '))}
                      </span>
                      <span className="rounded-full bg-green-200 px-2 py-0.5 text-xs font-medium text-green-800">
                        +{driver.contribution.toFixed(3)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-green-800">{driver.explanation}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Negative Drivers */}
      {explainability.top_negative_drivers.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-red-600" />
            <h3 className="text-lg font-semibold text-gray-900">Top Negative Drivers</h3>
            <span className="text-sm text-gray-500">
              ({explainability.top_negative_drivers.length})
            </span>
          </div>
          <div className="space-y-3">
            {explainability.top_negative_drivers.map((driver, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-red-200 bg-red-50 p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-red-900">
                        {capitalize(driver.feature.replace(/_/g, ' '))}
                      </span>
                      <span className="rounded-full bg-red-200 px-2 py-0.5 text-xs font-medium text-red-800">
                        {driver.contribution.toFixed(3)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-red-800">{driver.explanation}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Counterfactuals */}
      {explainability.counterfactuals && explainability.counterfactuals.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-yellow-600" />
            <h3 className="text-lg font-semibold text-gray-900">What-If Scenarios</h3>
            <span className="text-sm text-gray-500">
              ({explainability.counterfactuals.length})
            </span>
          </div>
          <div className="space-y-3">
            {explainability.counterfactuals.map((counterfactual, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-yellow-200 bg-yellow-50 p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="rounded-full bg-yellow-200 px-3 py-1 text-sm font-bold text-yellow-900">
                    {counterfactual.new_grade}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-yellow-900">
                      {counterfactual.explanation}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {Object.entries(counterfactual.field_changes).map(([field, value]) => (
                        <span
                          key={field}
                          className="rounded-md bg-yellow-100 px-2 py-1 text-xs font-medium text-yellow-800"
                        >
                          {capitalize(field.replace(/_/g, ' '))}: {String(value)}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SHAP Values */}
      {explainability.shap_values.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Award className="h-5 w-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">SHAP Feature Importance</h3>
          </div>
          <div className="rounded-lg border border-gray-200 overflow-hidden">
            <div className="max-h-96 overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Feature
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Impact
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                      Value
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {explainability.shap_values
                    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
                    .slice(0, 20)
                    .map((shap, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {capitalize(shap.feature.replace(/_/g, ' '))}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200">
                              <div
                                className={cn(
                                  'h-full',
                                  shap.value > 0 ? 'bg-green-600' : 'bg-red-600'
                                )}
                                style={{
                                  width: `${Math.min(Math.abs(shap.value) * 100, 100)}%`,
                                }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span
                            className={cn(
                              'text-sm font-medium',
                              shap.value > 0 ? 'text-green-600' : 'text-red-600'
                            )}
                          >
                            {shap.display_value}
                          </span>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
