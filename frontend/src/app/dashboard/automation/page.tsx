'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import {
  Zap,
  PlayCircle,
  PauseCircle,
  Shield,
  CheckCircle,
  AlertTriangle,
  Plus,
  Edit,
  Settings,
} from 'lucide-react'
import { format } from 'date-fns'

interface CadenceRule {
  id: string
  name: string
  description: string | null
  trigger: string
  steps: any[]
  enabled: boolean
  tags: string[]
  execution_count: number
  last_executed: string | null
  created_at: string
  updated_at: string
  created_by: string
}

export default function AutomationPage() {
  const { user } = useAuthStore()
  const [cadences, setCadences] = useState<CadenceRule[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'cadences' | 'compliance'>('cadences')

  useEffect(() => {
    fetchCadences()
  }, [])

  const fetchCadences = async () => {
    try {
      setLoading(true)
      const data = await apiClient.automation.getCadences()
      setCadences(data)
    } catch (error) {
      console.error('Failed to fetch cadences:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleCadence = async (id: string, currentlyEnabled: boolean) => {
    try {
      await apiClient.automation.toggleCadence(id, !currentlyEnabled)
      fetchCadences()
    } catch (error) {
      console.error('Failed to toggle cadence:', error)
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
            <h1 className="text-3xl font-bold text-gray-900">Automation</h1>
            <p className="text-gray-600 mt-1">
              Automated cadences, compliance, and workflow rules
            </p>
          </div>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2">
            <Plus className="h-4 w-4" />
            <span>New Cadence</span>
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Cadences</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {cadences.filter((c) => c.enabled).length}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <PlayCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Executions</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {cadences.reduce((sum, c) => sum + c.execution_count, 0)}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <Zap className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Compliance OK</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">98%</p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <Shield className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">DNC Blocks</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">12</p>
              </div>
              <div className="p-3 bg-red-100 rounded-lg">
                <AlertTriangle className="h-6 w-6 text-red-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-soft">
          <div className="border-b border-gray-200">
            <div className="flex">
              <button
                onClick={() => setActiveTab('cadences')}
                className={`px-6 py-4 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'cadences'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Zap className="h-4 w-4" />
                  <span>Cadence Rules ({cadences.length})</span>
                </div>
              </button>
              <button
                onClick={() => setActiveTab('compliance')}
                className={`px-6 py-4 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'compliance'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Shield className="h-4 w-4" />
                  <span>Compliance & DNC</span>
                </div>
              </button>
            </div>
          </div>

          <div className="p-6">
            {activeTab === 'cadences' && (
              <div className="space-y-4">
                {cadences.length === 0 ? (
                  <div className="text-center py-12">
                    <Zap className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      No cadences configured
                    </h3>
                    <p className="text-sm text-gray-600 mb-6">
                      Create automated sequences to engage with property owners
                    </p>
                    <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors inline-flex items-center space-x-2">
                      <Plus className="h-4 w-4" />
                      <span>Create Cadence</span>
                    </button>
                  </div>
                ) : (
                  cadences.map((cadence) => (
                    <div
                      key={cadence.id}
                      className={`border rounded-lg p-4 ${
                        cadence.enabled
                          ? 'border-gray-200 hover:border-gray-300'
                          : 'border-gray-200 bg-gray-50 opacity-75'
                      } transition-colors`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-3 flex-1">
                          <button
                            onClick={() => toggleCadence(cadence.id, cadence.enabled)}
                            className={`mt-1 p-1 rounded transition-colors ${
                              cadence.enabled
                                ? 'text-green-600 hover:bg-green-50'
                                : 'text-gray-400 hover:bg-gray-100'
                            }`}
                          >
                            {cadence.enabled ? (
                              <PlayCircle className="h-5 w-5" />
                            ) : (
                              <PauseCircle className="h-5 w-5" />
                            )}
                          </button>
                          <div className="flex-1">
                            <div className="flex items-center space-x-3 mb-2">
                              <h3 className="text-sm font-semibold text-gray-900">{cadence.name}</h3>
                              {cadence.enabled && (
                                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                                  Active
                                </span>
                              )}
                            </div>
                            {cadence.description && (
                              <p className="text-sm text-gray-600 mb-3">{cadence.description}</p>
                            )}
                            <div className="flex items-center space-x-4 mb-3">
                              <span className="text-xs text-gray-600">
                                Trigger: <span className="font-medium">{cadence.trigger}</span>
                              </span>
                              <span className="text-xs text-gray-600">
                                Steps: <span className="font-medium">{cadence.steps.length}</span>
                              </span>
                              <span className="text-xs text-gray-600">
                                Executions: <span className="font-medium">{cadence.execution_count}</span>
                              </span>
                            </div>
                            {cadence.tags.length > 0 && (
                              <div className="flex items-center space-x-2">
                                {cadence.tags.map((tag) => (
                                  <span
                                    key={tag}
                                    className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                                  >
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                            {cadence.last_executed && (
                              <p className="text-xs text-gray-500 mt-2">
                                Last executed: {format(new Date(cadence.last_executed), 'MMM d, yyyy h:mm a')}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center space-x-2 ml-4">
                          <button className="p-2 hover:bg-gray-100 rounded transition-colors">
                            <Edit className="h-4 w-4 text-gray-600" />
                          </button>
                          <button className="p-2 hover:bg-gray-100 rounded transition-colors">
                            <Settings className="h-4 w-4 text-gray-600" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'compliance' && (
              <div className="space-y-6">
                {/* Compliance Overview */}
                <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="h-6 w-6 text-green-600 mt-1" />
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 mb-2">
                        Compliance Status: Healthy
                      </h3>
                      <p className="text-sm text-gray-700 mb-4">
                        All automated communications are being checked for compliance with TCPA, CAN-SPAM,
                        and state regulations before sending.
                      </p>
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <p className="text-xs text-gray-600">Blocked Sends</p>
                          <p className="text-lg font-semibold text-gray-900">12</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-600">Warnings Issued</p>
                          <p className="text-lg font-semibold text-gray-900">38</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-600">Approved Sends</p>
                          <p className="text-lg font-semibold text-gray-900">1,842</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Do Not Contact List */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Do Not Contact (DNC)</h3>
                  <div className="border border-gray-200 rounded-lg divide-y divide-gray-200">
                    <div className="p-4 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">Federal DNC Registry</p>
                        <p className="text-xs text-gray-600 mt-1">Automatically checked before calls</p>
                      </div>
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                        Enabled
                      </span>
                    </div>
                    <div className="p-4 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">State DNC Lists</p>
                        <p className="text-xs text-gray-600 mt-1">CA, NY, TX, FL registries checked</p>
                      </div>
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                        Enabled
                      </span>
                    </div>
                    <div className="p-4 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">Internal DNC List</p>
                        <p className="text-xs text-gray-600 mt-1">23 contacts manually opted out</p>
                      </div>
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                        Active
                      </span>
                    </div>
                  </div>
                </div>

                {/* Consent Tracking */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Consent Management</h3>
                  <div className="border border-gray-200 rounded-lg p-4">
                    <p className="text-sm text-gray-700 mb-4">
                      Tracking explicit consent for email, SMS, and phone communications per TCPA/CAN-SPAM requirements.
                    </p>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center">
                        <p className="text-2xl font-bold text-gray-900">847</p>
                        <p className="text-xs text-gray-600 mt-1">Explicit Consent</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-gray-900">234</p>
                        <p className="text-xs text-gray-600 mt-1">Implied Consent</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-gray-900">23</p>
                        <p className="text-xs text-gray-600 mt-1">Opt-Outs</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
