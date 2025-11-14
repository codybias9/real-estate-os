/**
 * Portfolio Dashboard
 * Displays portfolio metrics tiles, template performance, and CSV export
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, TrendingUp, TrendingDown, Clock, Mail, MessageSquare, FileText } from 'lucide-react';

// ============================================================
// Types
// ============================================================

interface PortfolioTiles {
  total_leads: number;
  qualified_rate: number;
  avg_time_to_qualified_hrs: number;
  memo_conversion_rate: number;
  open_rate: number;
  reply_rate: number;
  window: string;
  calculated_at: string;
}

interface TemplatePerformance {
  template_id: string;
  template_name: string;
  channel: string;
  sends: number;
  delivery_rate: number;
  open_rate: number;
  click_rate: number;
  reply_rate: number;
}

interface PortfolioMetrics {
  tiles: PortfolioTiles;
  template_performance: TemplatePerformance[];
  daily_metrics: any[];
}

type TimeWindow = '7d' | '30d' | '90d' | '365d';

// ============================================================
// API Client
// ============================================================

async function fetchPortfolioMetrics(window: TimeWindow): Promise<PortfolioMetrics> {
  const response = await fetch(`/api/v1/metrics/portfolio?window=${window}`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch portfolio metrics');
  }

  return response.json();
}

async function exportFunnelCSV(window: TimeWindow): Promise<void> {
  const response = await fetch(`/api/v1/metrics/portfolio/export?window=${window}`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to export CSV');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `funnel_${window}_${new Date().toISOString().split('T')[0]}.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

// ============================================================
// Components
// ============================================================

interface MetricTileProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  subtitle?: string;
  color?: string;
}

function MetricTile({ icon, label, value, trend, subtitle, color = 'blue' }: MetricTileProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
    orange: 'bg-orange-50 text-orange-600 border-orange-200',
  };

  return (
    <div className={`p-6 rounded-lg border ${colorClasses[color]} shadow-sm hover:shadow-md transition-shadow`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-600 mb-2">
            {icon}
            <span>{label}</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">{value}</div>
          {subtitle && (
            <div className="text-sm text-gray-500 mt-1">{subtitle}</div>
          )}
        </div>
        {trend && (
          <div className={`${trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-gray-400'}`}>
            {trend === 'up' ? <TrendingUp size={20} /> : trend === 'down' ? <TrendingDown size={20} /> : null}
          </div>
        )}
      </div>
    </div>
  );
}

interface TemplateTableProps {
  templates: TemplatePerformance[];
}

function TemplateTable({ templates }: TemplateTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Template
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Channel
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Sends
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Delivery %
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Open %
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Click %
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Reply %
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {templates.map((template) => (
            <tr key={template.template_id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {template.template_name}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <span className={`px-2 py-1 rounded-full text-xs ${
                  template.channel === 'email' ? 'bg-blue-100 text-blue-800' :
                  template.channel === 'sms' ? 'bg-green-100 text-green-800' :
                  'bg-purple-100 text-purple-800'
                }`}>
                  {template.channel}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                {template.sends.toLocaleString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                {template.delivery_rate.toFixed(1)}%
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                {template.open_rate.toFixed(1)}%
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                {template.click_rate.toFixed(1)}%
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                <span className={`font-semibold ${
                  template.reply_rate >= 10 ? 'text-green-600' :
                  template.reply_rate >= 5 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {template.reply_rate.toFixed(1)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================
// Main Component
// ============================================================

export default function PortfolioDashboard() {
  const [window, setWindow] = useState<TimeWindow>('7d');
  const [isExporting, setIsExporting] = useState(false);

  const { data, isLoading, error, refetch } = useQuery<PortfolioMetrics>({
    queryKey: ['portfolio-metrics', window],
    queryFn: () => fetchPortfolioMetrics(window),
    refetchInterval: 60000, // Refresh every minute
  });

  const handleExportCSV = async () => {
    setIsExporting(true);
    try {
      await exportFunnelCSV(window);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to export CSV. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
        Failed to load portfolio metrics. Please try again.
      </div>
    );
  }

  const tiles = data?.tiles;
  const templates = data?.template_performance || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Last updated: {tiles ? new Date(tiles.calculated_at).toLocaleTimeString() : 'N/A'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Time window selector */}
          <select
            value={window}
            onChange={(e) => setWindow(e.target.value as TimeWindow)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="365d">Last 365 days</option>
          </select>

          {/* Export button */}
          <button
            onClick={handleExportCSV}
            disabled={isExporting}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            <Download size={16} />
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>
      </div>

      {/* Metric Tiles */}
      {tiles && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <MetricTile
            icon={<TrendingUp size={16} />}
            label="Total Leads"
            value={tiles.total_leads.toLocaleString()}
            subtitle={`Last ${tiles.window}`}
            color="blue"
          />
          <MetricTile
            icon={<FileText size={16} />}
            label="Qualified Rate"
            value={`${tiles.qualified_rate.toFixed(1)}%`}
            subtitle="Leads → Qualified"
            color="green"
          />
          <MetricTile
            icon={<Clock size={16} />}
            label="Avg Time to Qualified"
            value={`${tiles.avg_time_to_qualified_hrs.toFixed(1)}h`}
            subtitle="Median time to qualification"
            color="purple"
          />
          <MetricTile
            icon={<FileText size={16} />}
            label="Memo Conversion Rate"
            value={`${tiles.memo_conversion_rate.toFixed(1)}%`}
            subtitle="Qualified → Memo Generated"
            color="orange"
          />
          <MetricTile
            icon={<Mail size={16} />}
            label="Open Rate"
            value={`${tiles.open_rate.toFixed(1)}%`}
            subtitle="Outreach engagement"
            color="blue"
          />
          <MetricTile
            icon={<MessageSquare size={16} />}
            label="Reply Rate"
            value={`${tiles.reply_rate.toFixed(1)}%`}
            subtitle="Active conversations"
            color="green"
          />
        </div>
      )}

      {/* Template Performance Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Template Performance</h2>
          <p className="text-sm text-gray-500 mt-1">
            Sorted by reply rate (highest to lowest)
          </p>
        </div>
        <div className="p-6">
          {templates.length > 0 ? (
            <TemplateTable templates={templates} />
          ) : (
            <div className="text-center py-12 text-gray-500">
              No template performance data available for this period.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
