'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import {
  Database,
  TrendingUp,
  DollarSign,
  Activity,
  CheckCircle,
  AlertTriangle,
  Clock,
  Plus,
  RefreshCw,
  BarChart3,
} from 'lucide-react'
import { format } from 'date-fns'

interface EnrichmentStats {
  total_properties: number
  fully_enriched: number
  partially_enriched: number
  not_enriched: number
  average_completeness: number
  total_enrichment_cost_30d: number
  average_cost_per_property: number
  enrichment_jobs_24h: number
  failed_enrichments_24h: number
  sources_used: Record<string, number>
  average_enrichment_time: number
}

interface TrendingSignal {
  signal_type: string
  count_last_period: number
  count_previous_period: number
  trend_direction: 'up' | 'down' | 'stable'
  change_percentage: number
  average_strength: string
}

export default function DataPage() {
  const { user } = useAuthStore()
  const [stats, setStats] = useState<EnrichmentStats | null>(null)
  const [trendingSignals, setTrendingSignals] = useState<TrendingSignal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [statsData, signalsData] = await Promise.all([
        apiClient.data.getEnrichmentStats(),
        apiClient.data.getTrendingSignals(30, 6),
      ])
      setStats(statsData)
      setTrendingSignals(signalsData)
    } catch (error) {
      console.error('Failed to fetch data enrichment stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const getTrendIcon = (direction: string) => {
    switch (direction) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-green-600" />
      case 'down':
        return <TrendingUp className="h-4 w-4 text-red-600 rotate-180" />
      default:
        return <Activity className="h-4 w-4 text-gray-400" />
    }
  }

  const getSignalTypeLabel = (type: string) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount)
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
        </div>
      </DashboardLayout>
    )
  }

  if (!stats) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <p className="text-gray-600">Failed to load enrichment data</p>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Data & Enrichment</h1>
            <p className="text-gray-600 mt-1">
              Track data quality, enrichment jobs, and property signals
            </p>
          </div>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh Stats</span>
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Fully Enriched</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {stats.fully_enriched.toLocaleString()}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  of {stats.total_properties.toLocaleString()} properties
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <Database className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Completeness</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {stats.average_completeness}%
                </p>
                <p className="text-xs text-gray-500 mt-1">across all properties</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Cost (30 days)</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {formatCurrency(stats.total_enrichment_cost_30d)}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {formatCurrency(stats.average_cost_per_property)} avg/property
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <DollarSign className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Jobs (24h)</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {stats.enrichment_jobs_24h}
                </p>
                <p className="text-xs text-red-500 mt-1">
                  {stats.failed_enrichments_24h} failed
                </p>
              </div>
              <div className="p-3 bg-yellow-100 rounded-lg">
                <Activity className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Enrichment Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Data Sources */}
          <div className="bg-white rounded-lg shadow-soft p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Data Sources Usage</h2>
            <div className="space-y-3">
              {Object.entries(stats.sources_used)
                .sort(([, a], [, b]) => b - a)
                .map(([source, count]) => {
                  const maxCount = Math.max(...Object.values(stats.sources_used))
                  const percentage = (count / maxCount) * 100

                  return (
                    <div key={source}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700 capitalize">
                          {source.replace('_', ' ')}
                        </span>
                        <span className="text-sm text-gray-600">{count.toLocaleString()}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
            </div>
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between text-xs text-gray-600">
                <span>Average enrichment time</span>
                <span className="font-semibold">{stats.average_enrichment_time}s</span>
              </div>
            </div>
          </div>

          {/* Enrichment Status */}
          <div className="bg-white rounded-lg shadow-soft p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Enrichment Status</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                  <div>
                    <p className="text-sm font-semibold text-gray-900">Fully Enriched</p>
                    <p className="text-xs text-gray-600">Complete data available</p>
                  </div>
                </div>
                <p className="text-2xl font-bold text-green-600">
                  {stats.fully_enriched.toLocaleString()}
                </p>
              </div>

              <div className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Clock className="h-8 w-8 text-yellow-600" />
                  <div>
                    <p className="text-sm font-semibold text-gray-900">Partially Enriched</p>
                    <p className="text-xs text-gray-600">Some data missing</p>
                  </div>
                </div>
                <p className="text-2xl font-bold text-yellow-600">
                  {stats.partially_enriched.toLocaleString()}
                </p>
              </div>

              <div className="flex items-center justify-between p-4 bg-red-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <AlertTriangle className="h-8 w-8 text-red-600" />
                  <div>
                    <p className="text-sm font-semibold text-gray-900">Not Enriched</p>
                    <p className="text-xs text-gray-600">Needs enrichment</p>
                  </div>
                </div>
                <p className="text-2xl font-bold text-red-600">
                  {stats.not_enriched.toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Trending Signals */}
        <div className="bg-white rounded-lg shadow-soft">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Trending Signals</h2>
            <p className="text-sm text-gray-600 mb-4">
              Most frequently detected signals across your portfolio in the last 30 days
            </p>
            <div className="space-y-3">
              {trendingSignals.map((signal) => (
                <div
                  key={signal.signal_type}
                  className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-sm font-semibold text-gray-900">
                          {getSignalTypeLabel(signal.signal_type)}
                        </h3>
                        <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded capitalize">
                          {signal.average_strength}
                        </span>
                        <div className="flex items-center space-x-1">
                          {getTrendIcon(signal.trend_direction)}
                          <span
                            className={`text-xs font-medium ${
                              signal.trend_direction === 'up'
                                ? 'text-green-600'
                                : signal.trend_direction === 'down'
                                  ? 'text-red-600'
                                  : 'text-gray-600'
                            }`}
                          >
                            {signal.change_percentage > 0 ? '+' : ''}
                            {signal.change_percentage}%
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4 text-xs text-gray-600">
                        <span>Current period: {signal.count_last_period} detections</span>
                        <span>•</span>
                        <span>Previous period: {signal.count_previous_period}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
