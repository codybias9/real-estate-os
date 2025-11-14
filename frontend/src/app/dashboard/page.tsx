'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import Link from 'next/link'
import { ClientOnly } from '@/components/ClientOnly'
import {
  TrendingUp,
  Building2,
  Mail,
  CheckCircle,
  Clock,
  AlertCircle,
} from 'lucide-react'

interface DashboardStats {
  total_properties: number
  properties_by_stage: Record<string, number>
  recent_activity_count: number
  pending_tasks_count: number
  response_rate: number
  avg_days_in_pipeline: number
}

function DashboardPageContent() {
  const { user } = useAuthStore()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      if (!user?.team_id) return

      try {
        setLoading(true)
        // Fetch both pipeline stats and dashboard metrics in parallel
        const [pipelineData, dashboardData] = await Promise.all([
          apiClient.properties.getPipelineStats(user.team_id),
          apiClient.analytics.getDashboard(user.team_id),
        ])

        setStats({
          total_properties: pipelineData.total_properties || 0,
          properties_by_stage: pipelineData.stage_counts || {},
          recent_activity_count: pipelineData.properties_needing_contact || 0,
          pending_tasks_count: dashboardData.pending_tasks_count || 0,
          response_rate: dashboardData.response_rate || 0,
          avg_days_in_pipeline: dashboardData.avg_days_to_close || 0,
        })
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [user?.team_id])

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome back, {user?.full_name?.split(' ')[0]}
          </h1>
          <p className="text-gray-600 mt-1">
            Here's what's happening with your pipeline today
          </p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white rounded-lg shadow-soft p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
                <div className="h-8 bg-gray-200 rounded w-3/4" />
              </div>
            ))}
          </div>
        ) : (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Total Properties */}
              <div className="bg-white rounded-lg shadow-soft p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Properties</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {stats?.total_properties || 0}
                    </p>
                  </div>
                  <div className="p-3 bg-primary-100 rounded-lg">
                    <Building2 className="h-6 w-6 text-primary-600" />
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm text-green-600">
                  <TrendingUp className="h-4 w-4 mr-1" />
                  <span>12% from last month</span>
                </div>
              </div>

              {/* Pending Actions */}
              <div className="bg-white rounded-lg shadow-soft p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Needs Contact</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {stats?.recent_activity_count || 0}
                    </p>
                  </div>
                  <div className="p-3 bg-orange-100 rounded-lg">
                    <Clock className="h-6 w-6 text-orange-600" />
                  </div>
                </div>
                <div className="mt-4">
                  <Link
                    href="/dashboard/pipeline"
                    className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                  >
                    View pipeline →
                  </Link>
                </div>
              </div>

              {/* Response Rate */}
              <div className="bg-white rounded-lg shadow-soft p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Response Rate</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {Math.round((stats?.response_rate || 0) * 100)}%
                    </p>
                  </div>
                  <div className="p-3 bg-green-100 rounded-lg">
                    <Mail className="h-6 w-6 text-green-600" />
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm text-green-600">
                  <TrendingUp className="h-4 w-4 mr-1" />
                  <span>5% improvement</span>
                </div>
              </div>

              {/* Avg Days in Pipeline */}
              <div className="bg-white rounded-lg shadow-soft p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Avg Days</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {stats?.avg_days_in_pipeline || 0}
                    </p>
                  </div>
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <CheckCircle className="h-6 w-6 text-blue-600" />
                  </div>
                </div>
                <div className="mt-4 text-sm text-gray-600">
                  Time to close
                </div>
              </div>
            </div>

            {/* Stage Breakdown */}
            <div className="bg-white rounded-lg shadow-soft p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Pipeline by Stage
              </h2>
              <div className="space-y-3">
                {Object.entries(stats?.properties_by_stage || {}).map(([stage, count]) => (
                  <div key={stage} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          stage === 'new'
                            ? 'bg-blue-500'
                            : stage === 'outreach'
                            ? 'bg-yellow-500'
                            : stage === 'qualified'
                            ? 'bg-green-500'
                            : stage === 'negotiation'
                            ? 'bg-purple-500'
                            : stage === 'under_contract'
                            ? 'bg-indigo-500'
                            : stage === 'closed_won'
                            ? 'bg-green-600'
                            : 'bg-gray-400'
                        }`}
                      />
                      <span className="text-sm font-medium text-gray-700 capitalize">
                        {stage.replace('_', ' ')}
                      </span>
                    </div>
                    <span className="text-sm font-semibold text-gray-900">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-gradient-to-br from-primary-50 to-secondary-50 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Link
                  href="/dashboard/pipeline"
                  className="bg-white p-4 rounded-lg hover:shadow-medium transition-shadow"
                >
                  <Building2 className="h-8 w-8 text-primary-600 mb-2" />
                  <h3 className="font-semibold text-gray-900">View Pipeline</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Manage your deal pipeline
                  </p>
                </Link>

                <Link
                  href="/dashboard/communications"
                  className="bg-white p-4 rounded-lg hover:shadow-medium transition-shadow"
                >
                  <Mail className="h-8 w-8 text-primary-600 mb-2" />
                  <h3 className="font-semibold text-gray-900">Send Outreach</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Generate and send memos
                  </p>
                </Link>

                <Link
                  href="/dashboard/portfolio"
                  className="bg-white p-4 rounded-lg hover:shadow-medium transition-shadow"
                >
                  <CheckCircle className="h-8 w-8 text-primary-600 mb-2" />
                  <h3 className="font-semibold text-gray-900">View Portfolio</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Track deal economics
                  </p>
                </Link>
              </div>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  )
}

export default function DashboardPage() {
  return (
    <ClientOnly
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-gray-400">Loading...</div>
        </div>
      }
    >
      <DashboardPageContent />
    </ClientOnly>
  )
}
