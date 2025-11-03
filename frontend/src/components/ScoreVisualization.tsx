/**
 * Score visualization with explainability
 */

import type { ScoreResult } from '@/types';
import { LoadingSpinner } from './LoadingSpinner';
import { getScoreBadgeColor } from '@/lib/utils';

interface ScoreVisualizationProps {
  score: number | undefined;
  scoreResult: ScoreResult | undefined;
  isLoading: boolean;
}

export function ScoreVisualization({ score, scoreResult, isLoading }: ScoreVisualizationProps) {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (!score || !scoreResult) {
    return (
      <div className="text-center text-gray-500 py-12">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <p className="mt-4">Property has not been scored yet</p>
      </div>
    );
  }

  const scoreLabel =
    score >= 80 ? 'Excellent' : score >= 60 ? 'Good' : score >= 40 ? 'Fair' : 'Poor';

  return (
    <div className="space-y-6">
      {/* Score Badge */}
      <div className="flex items-center justify-center">
        <div className="text-center">
          <div
            className={`w-32 h-32 rounded-full ${getScoreBadgeColor(
              score
            )} flex items-center justify-center mx-auto`}
          >
            <span className="text-5xl font-bold text-white">{score}</span>
          </div>
          <p className="mt-4 text-lg font-medium text-gray-900">{scoreLabel} Investment</p>
          <p className="text-sm text-gray-500">Model: {scoreResult.model_version}</p>
        </div>
      </div>

      {/* Score Breakdown */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Score Breakdown</h3>
        <div className="space-y-3">
          {scoreResult.reasons.map((reason, index) => {
            const percentage = Math.round(reason.weight * 100);
            const direction = reason.direction;

            return (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-900 capitalize">
                      {reason.feature.replace(/_/g, ' ')}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        direction === 'positive'
                          ? 'bg-green-100 text-green-800'
                          : direction === 'negative'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {direction === 'positive' ? '↑' : direction === 'negative' ? '↓' : '→'}
                    </span>
                  </div>
                  <span className="text-sm font-medium text-gray-700">{percentage}% weight</span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className={`h-2 rounded-full ${
                      direction === 'positive'
                        ? 'bg-green-500'
                        : direction === 'negative'
                          ? 'bg-red-500'
                          : 'bg-gray-400'
                    }`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>

                <p className="text-sm text-gray-600">{reason.note}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Scoring Details */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-2">How This Score Was Calculated</h4>
        <p className="text-sm text-gray-600">
          The investment score is a weighted combination of {scoreResult.reasons.length} factors,
          each contributing to the overall assessment of this property's investment potential.
          Higher weights indicate more important factors in the scoring model.
        </p>
      </div>
    </div>
  );
}
