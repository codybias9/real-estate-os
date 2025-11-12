'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import {
  DollarSign,
  TrendingUp,
  Calendar,
  BarChart3,
  Target,
  Award,
  Building2,
} from 'lucide-react'

interface PortfolioMetrics {
  total_properties: number
  total_deal_value: number
  avg_deal_size: number
  win_rate: number
  avg_days_to_close: number
  pipeline_value: number
  closed_deals_count: number
  active_deals_count: number
}

export default function PortfolioPage() {
  const { user } = useAuthStore()
  const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMetrics()
  }, [user?.team_id])

  const fetchMetrics = async () => {
    if (!user?.team_id) return

    try {
      setLoading(true)
      const data = await apiClient.portfolio.getMetrics(user.team_id)
      setMetrics(data)
    } catch (error) {
      console.error('Failed to fetch portfolio metrics:', error)
      // Set default values if API fails
      setMetrics({
        total_properties: 0,
        total_deal_value: 0,
        avg_deal_size: 0,
        win_rate: 0,
        avg_days_to_close: 0,
        pipeline_value: 0,
        closed_deals_count: 0,
        active_deals_count: 0,
      })
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-3xl font-bold text-gray-900">Portfolio</h1>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="bg-white rounded-lg shadow-soft p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
                <div className="h-8 bg-gray-200 rounded w-3/4" />
              </div>
            ))}
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Portfolio</h1>
          <p className="text-gray-600 mt-1">Track your deal performance and economics</p>
        </div>

        {/* Metric Tiles */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Total Deal Value */}
          <div className="bg-white rounded-lg shadow-soft p-6 hover:shadow-medium transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Deal Value</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {formatCurrency(metrics?.total_deal_value || 0)}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <DollarSign className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-gray-600">
              <Building2 className="h-4 w-4 mr-1" />
              <span>{metrics?.closed_deals_count || 0} closed deals</span>
            </div>
          </div>

          {/* Average Deal Size */}
          <div className="bg-white rounded-lg shadow-soft p-6 hover:shadow-medium transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Deal Size</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {formatCurrency(metrics?.avg_deal_size || 0)}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-600">
              Per closed deal
            </div>
          </div>

          {/* Win Rate */}
          <div className="bg-white rounded-lg shadow-soft p-6 hover:shadow-medium transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Win Rate</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {formatPercentage(metrics?.win_rate || 0)}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <Target className="h-6 w-6 text-purple-600" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-green-600">
              <TrendingUp className="h-4 w-4 mr-1" />
              <span>Above industry avg</span>
            </div>
          </div>

          {/* Average Days to Close */}
          <div className="bg-white rounded-lg shadow-soft p-6 hover:shadow-medium transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Days to Close</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {Math.round(metrics?.avg_days_to_close || 0)}
                </p>
              </div>
              <div className="p-3 bg-orange-100 rounded-lg">
                <Calendar className="h-6 w-6 text-orange-600" />
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-600">
              From outreach to close
            </div>
          </div>

          {/* Pipeline Value */}
          <div className="bg-white rounded-lg shadow-soft p-6 hover:shadow-medium transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Pipeline Value</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {formatCurrency(metrics?.pipeline_value || 0)}
                </p>
              </div>
              <div className="p-3 bg-indigo-100 rounded-lg">
                <TrendingUp className="h-6 w-6 text-indigo-600" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-gray-600">
              <Building2 className="h-4 w-4 mr-1" />
              <span>{metrics?.active_deals_count || 0} active deals</span>
            </div>
          </div>

          {/* Total Properties */}
          <div className="bg-white rounded-lg shadow-soft p-6 hover:shadow-medium transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Properties</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {metrics?.total_properties || 0}
                </p>
              </div>
              <div className="p-3 bg-yellow-100 rounded-lg">
                <Award className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-600">
              All time in pipeline
            </div>
          </div>
        </div>

        {/* Additional Sections */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Quick Stats */}
          <div className="bg-white rounded-lg shadow-soft p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Performance Insights</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-sm font-medium text-gray-700">Closed Won</span>
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  {metrics?.closed_deals_count || 0}
                </span>
              </div>

              <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <span className="text-sm font-medium text-gray-700">Active Pipeline</span>
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  {metrics?.active_deals_count || 0}
                </span>
              </div>

              <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-purple-500" />
                  <span className="text-sm font-medium text-gray-700">Conversion Rate</span>
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  {formatPercentage(metrics?.win_rate || 0)}
                </span>
              </div>
            </div>
          </div>

          {/* Revenue Breakdown */}
          <div className="bg-gradient-to-br from-primary-50 to-secondary-50 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Revenue Summary</h2>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Total Revenue</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {formatCurrency(metrics?.total_deal_value || 0)}
                  </span>
                </div>
                <div className="w-full bg-white rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Pipeline Value</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {formatCurrency(metrics?.pipeline_value || 0)}
                  </span>
                </div>
                <div className="w-full bg-white rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{
                      width: `${
                        metrics?.total_deal_value
                          ? Math.min(
                              100,
                              ((metrics?.pipeline_value || 0) / metrics.total_deal_value) * 100
                            )
                          : 50
                      }%`,
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-white">
              <p className="text-sm text-gray-600">
                Your pipeline represents{' '}
                <span className="font-semibold text-gray-900">
                  {metrics?.total_deal_value
                    ? formatPercentage(
                        (metrics?.pipeline_value || 0) / metrics.total_deal_value
                      )
                    : '0%'}
                </span>{' '}
                of your closed revenue
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
