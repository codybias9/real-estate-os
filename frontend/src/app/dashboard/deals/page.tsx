'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import {
  DollarSign,
  TrendingUp,
  Calendar,
  Plus,
  CheckCircle,
  Clock,
  Building2,
} from 'lucide-react'
import { format } from 'date-fns'

interface Deal {
  id: number
  property_id: number
  offer_amount: number | null
  estimated_arv: number | null
  estimated_repair_cost: number | null
  expected_profit: number | null
  profit_margin: number | null
  investor_id: number | null
  projected_close_date: string | null
  probability_of_close: number | null
  status: 'pending' | 'accepted' | 'rejected' | 'in_escrow' | 'closed'
  created_at: string
}

export default function DealsPage() {
  const { user } = useAuthStore()
  const [deals, setDeals] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDeals()
  }, [])

  const fetchDeals = async () => {
    try {
      setLoading(true)
      const data = await apiClient.deals.list()
      setDeals(data)
    } catch (error) {
      console.error('Failed to fetch deals:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'closed':
        return 'bg-green-100 text-green-700'
      case 'in_escrow':
        return 'bg-blue-100 text-blue-700'
      case 'accepted':
        return 'bg-purple-100 text-purple-700'
      case 'pending':
        return 'bg-yellow-100 text-yellow-700'
      case 'rejected':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const formatCurrency = (amount: number | null) => {
    if (amount === null) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
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

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Deals</h1>
            <p className="text-gray-600 mt-1">
              Track deal economics, ARV, and profitability
            </p>
          </div>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2">
            <Plus className="h-4 w-4" />
            <span>New Deal</span>
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Deals</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{deals.length}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <Building2 className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Pipeline Value</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {formatCurrency(
                    deals.reduce((sum, d) => sum + (d.offer_amount || 0), 0)
                  )}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <DollarSign className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Expected Profit</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {formatCurrency(
                    deals.reduce((sum, d) => sum + (d.expected_profit || 0), 0)
                  )}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Close Probability</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {deals.length > 0
                    ? Math.round(
                        (deals.reduce((sum, d) => sum + (d.probability_of_close || 0), 0) /
                          deals.length) *
                          100
                      )
                    : 0}
                  %
                </p>
              </div>
              <div className="p-3 bg-yellow-100 rounded-lg">
                <CheckCircle className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Deals List */}
        <div className="bg-white rounded-lg shadow-soft">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">All Deals</h2>
            {deals.length === 0 ? (
              <div className="text-center py-12">
                <Building2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No deals yet</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Start tracking deal economics and profitability
                </p>
                <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors inline-flex items-center space-x-2">
                  <Plus className="h-4 w-4" />
                  <span>Create Deal</span>
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {deals.map((deal) => (
                  <div
                    key={deal.id}
                    className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-sm font-semibold text-gray-900">
                            Deal #{deal.id}
                          </h3>
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${getStatusColor(
                              deal.status
                            )}`}
                          >
                            {deal.status.replace('_', ' ')}
                          </span>
                          {deal.probability_of_close && (
                            <span className="text-xs text-gray-600">
                              {Math.round(deal.probability_of_close * 100)}% likely
                            </span>
                          )}
                        </div>
                        {deal.projected_close_date && (
                          <div className="flex items-center space-x-1 text-xs text-gray-600">
                            <Calendar className="h-3 w-3" />
                            <span>
                              Close: {format(new Date(deal.projected_close_date), 'MMM d, yyyy')}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-4 gap-4">
                      <div>
                        <p className="text-xs text-gray-600">Offer Amount</p>
                        <p className="text-sm font-semibold text-gray-900">
                          {formatCurrency(deal.offer_amount)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600">ARV</p>
                        <p className="text-sm font-semibold text-gray-900">
                          {formatCurrency(deal.estimated_arv)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600">Repair Cost</p>
                        <p className="text-sm font-semibold text-gray-900">
                          {formatCurrency(deal.estimated_repair_cost)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600">Expected Profit</p>
                        <p className="text-sm font-semibold text-green-600">
                          {formatCurrency(deal.expected_profit)}
                        </p>
                      </div>
                    </div>
                    {deal.profit_margin && (
                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-600">Profit Margin</span>
                          <span className="font-semibold text-green-600">
                            {Math.round(deal.profit_margin * 100)}%
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
