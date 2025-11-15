'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { dashboardApi } from '@/lib/api';
import { PipelineStage } from '@/types';

interface PipelineStats {
  stages: PipelineStage[];
  total: number;
  recent_runs: DagRun[];
  errors: PipelineError[];
}

interface DagRun {
  dag_id: string;
  run_id: string;
  state: string;
  execution_date: string;
  start_date: string;
  end_date?: string;
}

interface PipelineError {
  property_id: number;
  address: string;
  stage: string;
  error_message: string;
  timestamp: string;
}

export default function PipelinePage() {
  const [pipelineData, setPipelineData] = useState<PipelineStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPipelineData();
  }, []);

  const loadPipelineData = async () => {
    try {
      const response = await dashboardApi.pipeline();
      setPipelineData(response.data);
    } catch (error) {
      console.error('Error loading pipeline:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStageColor = (stageName: string) => {
    const colors: Record<string, string> = {
      'Discovery': 'bg-blue-500',
      'Enrichment': 'bg-purple-500',
      'Scoring': 'bg-yellow-500',
      'Documentation': 'bg-green-500',
      'Outreach': 'bg-red-500',
    };
    return colors[stageName] || 'bg-gray-500';
  };

  const getStateBadge = (state: string) => {
    const badges: Record<string, string> = {
      success: 'badge-success',
      running: 'badge-info',
      failed: 'badge-danger',
      queued: 'badge-warning',
    };
    return badges[state] || 'badge-info';
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center py-12">Loading pipeline...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="md:flex md:items-center md:justify-between mb-8">
        <div className="flex-1 min-w-0">
          <h1 className="text-3xl font-bold text-gray-900">Data Pipeline</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor property processing through the automated pipeline
          </p>
        </div>
        <div className="mt-4 flex md:mt-0 md:ml-4">
          <button className="btn-primary">Trigger Manual Run</button>
        </div>
      </div>

      {/* Pipeline Flow Visualization */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-6">Pipeline Stages</h2>
        <div className="relative">
          {/* Pipeline Flow */}
          <div className="flex items-center justify-between mb-8">
            {pipelineData?.stages.map((stage, idx) => (
              <div key={stage.name} className="flex items-center flex-1">
                <Link href={`/properties?status=${stage.name.toLowerCase()}`}>
                  <div className="flex flex-col items-center cursor-pointer hover:opacity-80 transition-opacity">
                    <div className={`w-20 h-20 rounded-full ${getStageColor(stage.name)} flex items-center justify-center text-white shadow-lg`}>
                      <span className="text-2xl font-bold">{stage.count}</span>
                    </div>
                    <div className="mt-2 text-sm font-medium text-gray-900">{stage.name}</div>
                    <div className="text-xs text-gray-500">{stage.percentage}%</div>
                  </div>
                </Link>
                {idx < (pipelineData?.stages.length || 0) - 1 && (
                  <div className="flex-1 h-1 bg-gray-300 mx-4">
                    <div
                      className="h-full bg-primary-500 transition-all"
                      style={{ width: `${stage.percentage}%` }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Stage Details */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {pipelineData?.stages.map((stage) => (
              <div key={stage.name} className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-2">{stage.name}</h3>
                <p className="text-2xl font-bold text-gray-900 mb-1">{stage.count}</p>
                <p className="text-xs text-gray-500">properties in stage</p>
                <div className="mt-3">
                  <Link
                    href={`/properties?status=${stage.name.toLowerCase()}`}
                    className="text-xs text-primary-600 hover:text-primary-700"
                  >
                    View properties →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent DAG Runs */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent DAG Runs</h2>
          <div className="space-y-3">
            {pipelineData?.recent_runs && pipelineData.recent_runs.length > 0 ? (
              pipelineData.recent_runs.map((run) => (
                <div key={run.run_id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-gray-900">{run.dag_id}</h3>
                      <p className="text-xs text-gray-500 mt-1">Run ID: {run.run_id}</p>
                    </div>
                    <span className={`badge ${getStatebadge(run.state)}`}>
                      {run.state}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                    <div>
                      <span className="text-gray-500">Started:</span>{' '}
                      {new Date(run.start_date).toLocaleString()}
                    </div>
                    {run.end_date && (
                      <div>
                        <span className="text-gray-500">Ended:</span>{' '}
                        {new Date(run.end_date).toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-500 text-sm">
                No recent DAG runs. Pipeline may be idle or data unavailable.
              </div>
            )}
          </div>
        </div>

        {/* Recent Errors */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Errors</h2>
          <div className="space-y-3">
            {pipelineData?.errors && pipelineData.errors.length > 0 ? (
              pipelineData.errors.map((error, idx) => (
                <div key={idx} className="border border-red-200 bg-red-50 rounded-lg p-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <Link
                        href={`/properties/${error.property_id}`}
                        className="text-sm font-semibold text-gray-900 hover:text-primary-600"
                      >
                        {error.address}
                      </Link>
                      <p className="text-xs text-gray-500 mt-1">Stage: {error.stage}</p>
                    </div>
                    <span className="text-xs text-gray-500">
                      {new Date(error.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-red-700">{error.error_message}</p>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-500 text-sm">
                No errors found. All pipeline stages running smoothly!
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pipeline Metrics */}
      <div className="card mt-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Metrics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="border-l-4 border-blue-500 pl-4">
            <p className="text-sm text-gray-600">Total Properties</p>
            <p className="text-2xl font-bold text-gray-900">{pipelineData?.total || 0}</p>
          </div>
          <div className="border-l-4 border-green-500 pl-4">
            <p className="text-sm text-gray-600">Completion Rate</p>
            <p className="text-2xl font-bold text-gray-900">
              {pipelineData?.stages && pipelineData.total
                ? Math.round((pipelineData.stages[pipelineData.stages.length - 1]?.count || 0) / pipelineData.total * 100)
                : 0}%
            </p>
          </div>
          <div className="border-l-4 border-yellow-500 pl-4">
            <p className="text-sm text-gray-600">Processing</p>
            <p className="text-2xl font-bold text-gray-900">
              {pipelineData?.stages
                ? pipelineData.stages.slice(0, -1).reduce((sum, s) => sum + s.count, 0)
                : 0}
            </p>
          </div>
          <div className="border-l-4 border-red-500 pl-4">
            <p className="text-sm text-gray-600">Error Rate</p>
            <p className="text-2xl font-bold text-gray-900">
              {pipelineData?.errors && pipelineData.total
                ? ((pipelineData.errors.length / pipelineData.total) * 100).toFixed(1)
                : 0}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
