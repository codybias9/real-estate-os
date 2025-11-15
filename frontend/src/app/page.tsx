'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { dashboardApi } from '@/lib/api';
import { DashboardStats, PipelineStage } from '@/types';

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pipeline, setPipeline] = useState<{stages: PipelineStage[], total: number} | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [statsRes, pipelineRes] = await Promise.all([
        dashboardApi.stats(),
        dashboardApi.pipeline(),
      ]);
      setStats(statsRes.data);
      setPipeline(pipelineRes.data);
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="md:flex md:items-center md:justify-between mb-8">
        <div className="flex-1 min-w-0">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">Overview of your real estate investment pipeline</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatCard
          title="Total Properties"
          value={stats?.properties.total || 0}
          change={`+${stats?.properties.recent_30_days || 0} this month`}
          trend="up"
        />
        <StatCard
          title="Enriched"
          value={stats?.properties.enriched || 0}
          subtitle={`${((stats?.properties.enriched || 0) / (stats?.properties.total || 1) * 100).toFixed(0)}% of total`}
        />
        <StatCard
          title="Scored"
          value={stats?.properties.scored || 0}
          subtitle={`Avg: ${stats?.scoring.average_score.toFixed(1)}/100`}
        />
        <StatCard
          title="High Quality"
          value={stats?.scoring.high_score_count || 0}
          subtitle="Score ≥ 80"
          highlight
        />
      </div>

      {/* Pipeline Status */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Status</h2>
        <div className="space-y-4">
          {pipeline?.stages.map((stage) => (
            <div key={stage.name}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">{stage.name}</span>
                <span className="text-sm text-gray-500">
                  {stage.count} ({stage.percentage}%)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-primary-600 h-2 rounded-full transition-all"
                  style={{ width: `${stage.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t">
          <div className="text-sm text-gray-500">
            Total Properties in Pipeline: <span className="font-semibold text-gray-900">{pipeline?.total || 0}</span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link href="/properties" className="block">
              <div className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">View All Properties</div>
                  <div className="text-xs text-gray-500">Browse and filter properties</div>
                </div>
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
            <Link href="/properties?status=new" className="block">
              <div className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">New Discoveries</div>
                  <div className="text-xs text-gray-500">{stats?.properties.new || 0} properties await enrichment</div>
                </div>
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
            <Link href="/campaigns" className="block">
              <div className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">Email Campaigns</div>
                  <div className="text-xs text-gray-500">{stats?.campaigns.total || 0} campaigns, {stats?.campaigns.active || 0} active</div>
                </div>
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">System Health</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">API Status</span>
              <span className="badge-success">Online</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Database</span>
              <span className="badge-success">Connected</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Airflow DAGs</span>
              <span className="badge-success">Running</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Last Scrape</span>
              <span className="text-sm font-medium text-gray-900">2 hours ago</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, subtitle, change, trend, highlight }: {
  title: string;
  value: number;
  subtitle?: string;
  change?: string;
  trend?: 'up' | 'down';
  highlight?: boolean;
}) {
  return (
    <div className={`card ${highlight ? 'border-primary-500 bg-primary-50' : ''}`}>
      <div className="flex items-center">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className={`mt-1 text-3xl font-semibold ${highlight ? 'text-primary-700' : 'text-gray-900'}`}>
            {value.toLocaleString()}
          </p>
          {subtitle && (
            <p className="mt-1 text-xs text-gray-500">{subtitle}</p>
          )}
          {change && (
            <p className={`mt-1 text-xs ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
              {change}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
