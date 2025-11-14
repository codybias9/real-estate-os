'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import {
  Users,
  Mail,
  Phone,
  Plus,
  Filter,
  TrendingUp,
  CheckCircle,
} from 'lucide-react'
import { format } from 'date-fns'

interface Lead {
  id: string
  name: string
  email: string
  phone: string | null
  source: string
  status: string
  notes: string | null
  created_at: string
}

export default function LeadsPage() {
  const { user } = useAuthStore()
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLeads()
  }, [])

  const fetchLeads = async () => {
    try {
      setLoading(true)
      const data = await apiClient.leads.list()
      setLeads(data)
    } catch (error) {
      console.error('Failed to fetch leads:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'qualified':
        return 'bg-green-100 text-green-700'
      case 'contacted':
        return 'bg-blue-100 text-blue-700'
      case 'new':
        return 'bg-yellow-100 text-yellow-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
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
            <h1 className="text-3xl font-bold text-gray-900">Leads</h1>
            <p className="text-gray-600 mt-1">
              Track and manage your buyer and investor leads
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-2">
              <Filter className="h-4 w-4" />
              <span>Filter</span>
            </button>
            <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2">
              <Plus className="h-4 w-4" />
              <span>New Lead</span>
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Leads</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{leads.length}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">New Leads</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {leads.filter((l) => l.status === 'new').length}
                </p>
              </div>
              <div className="p-3 bg-yellow-100 rounded-lg">
                <TrendingUp className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Contacted</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {leads.filter((l) => l.status === 'contacted').length}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <Mail className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Qualified</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {leads.filter((l) => l.status === 'qualified').length}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Leads List */}
        <div className="bg-white rounded-lg shadow-soft">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">All Leads</h2>
            {leads.length === 0 ? (
              <div className="text-center py-12">
                <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No leads yet</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Start adding leads to track your buyers and investors
                </p>
                <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors inline-flex items-center space-x-2">
                  <Plus className="h-4 w-4" />
                  <span>Add Lead</span>
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {leads.map((lead) => (
                  <div
                    key={lead.id}
                    className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-sm font-semibold text-gray-900">{lead.name}</h3>
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${getStatusColor(
                              lead.status
                            )}`}
                          >
                            {lead.status}
                          </span>
                          <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                            {lead.source}
                          </span>
                        </div>
                        <div className="flex items-center space-x-4 text-sm text-gray-600 mb-2">
                          <div className="flex items-center space-x-1">
                            <Mail className="h-3 w-3" />
                            <span>{lead.email}</span>
                          </div>
                          {lead.phone && (
                            <div className="flex items-center space-x-1">
                              <Phone className="h-3 w-3" />
                              <span>{lead.phone}</span>
                            </div>
                          )}
                        </div>
                        {lead.notes && (
                          <p className="text-xs text-gray-600">{lead.notes}</p>
                        )}
                        <p className="text-xs text-gray-500 mt-2">
                          Added {format(new Date(lead.created_at), 'MMM d, yyyy')}
                        </p>
                      </div>
                    </div>
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
