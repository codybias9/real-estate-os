'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import {
  List,
  Zap,
  CheckCircle,
  Clock,
  AlertCircle,
  TrendingUp,
  Filter,
  Plus,
  ChevronRight,
} from 'lucide-react'
import { format } from 'date-fns'

interface SmartList {
  id: string
  name: string
  description: string | null
  filters: any[]
  tags: string[]
  property_count: number
  created_at: string
  updated_at: string
  created_by: string
}

interface NextBestAction {
  id: string
  property_id: string
  action_type: string
  title: string
  description: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: 'pending' | 'in_progress' | 'completed' | 'dismissed'
  reasoning: string
  estimated_impact: string
  estimated_effort: string
  due_date: string | null
  completed_at: string | null
  completed_by: string | null
  created_at: string
}

export default function WorkflowPage() {
  const { user } = useAuthStore()
  const [smartLists, setSmartLists] = useState<SmartList[]>([])
  const [actions, setActions] = useState<NextBestAction[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'actions' | 'lists'>('actions')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [listsData, actionsData] = await Promise.all([
        apiClient.workflow.getSmartLists(),
        apiClient.workflow.getNextBestActions(),
      ])
      setSmartLists(listsData)
      setActions(actionsData)
    } catch (error) {
      console.error('Failed to fetch workflow data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-100 text-red-700 border-red-200'
      case 'high':
        return 'bg-orange-100 text-orange-700 border-orange-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      case 'low':
        return 'bg-blue-100 text-blue-700 border-blue-200'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-600" />
      case 'pending':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
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
            <h1 className="text-3xl font-bold text-gray-900">Workflow</h1>
            <p className="text-gray-600 mt-1">
              Smart lists and AI-powered next-best-actions
            </p>
          </div>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2">
            <Plus className="h-4 w-4" />
            <span>New Smart List</span>
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Actions</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {actions.filter((a) => a.status === 'pending' || a.status === 'in_progress').length}
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
                <p className="text-sm font-medium text-gray-600">High Priority</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {actions.filter((a) => a.priority === 'high' || a.priority === 'urgent').length}
                </p>
              </div>
              <div className="p-3 bg-orange-100 rounded-lg">
                <AlertCircle className="h-6 w-6 text-orange-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Smart Lists</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{smartLists.length}</p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <List className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Completed Today</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {actions.filter((a) => a.status === 'completed').length}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-soft">
          <div className="border-b border-gray-200">
            <div className="flex">
              <button
                onClick={() => setActiveTab('actions')}
                className={`px-6 py-4 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'actions'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Zap className="h-4 w-4" />
                  <span>Next-Best-Actions ({actions.length})</span>
                </div>
              </button>
              <button
                onClick={() => setActiveTab('lists')}
                className={`px-6 py-4 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'lists'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <List className="h-4 w-4" />
                  <span>Smart Lists ({smartLists.length})</span>
                </div>
              </button>
            </div>
          </div>

          <div className="p-6">
            {activeTab === 'actions' && (
              <div className="space-y-4">
                {actions.length === 0 ? (
                  <div className="text-center py-12">
                    <Zap className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      No actions yet
                    </h3>
                    <p className="text-sm text-gray-600">
                      Next-best-actions will appear here automatically
                    </p>
                  </div>
                ) : (
                  actions.map((action) => (
                    <div
                      key={action.id}
                      className={`border rounded-lg p-4 hover:border-gray-300 transition-colors ${
                        action.status === 'completed' ? 'opacity-60' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-3 flex-1">
                          <div className="mt-1">{getStatusIcon(action.status)}</div>
                          <div className="flex-1">
                            <div className="flex items-center space-x-3 mb-2">
                              <h3 className="text-sm font-semibold text-gray-900">
                                {action.title}
                              </h3>
                              <span
                                className={`text-xs px-2 py-0.5 rounded border ${getPriorityColor(
                                  action.priority
                                )}`}
                              >
                                {action.priority}
                              </span>
                              <span className="text-xs text-gray-500 capitalize">
                                {action.action_type}
                              </span>
                            </div>
                            <p className="text-sm text-gray-700 mb-2">{action.description}</p>
                            <div className="bg-blue-50 rounded p-3 mb-3">
                              <p className="text-xs text-gray-700">
                                <span className="font-medium">AI Reasoning:</span> {action.reasoning}
                              </p>
                            </div>
                            <div className="flex items-center space-x-4 text-xs text-gray-600">
                              <span>Impact: {action.estimated_impact}</span>
                              <span>•</span>
                              <span>Effort: {action.estimated_effort}</span>
                              {action.due_date && (
                                <>
                                  <span>•</span>
                                  <span>Due: {format(new Date(action.due_date), 'MMM d')}</span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        <button className="ml-4 p-2 hover:bg-gray-100 rounded transition-colors">
                          <ChevronRight className="h-5 w-5 text-gray-400" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'lists' && (
              <div className="space-y-4">
                {smartLists.length === 0 ? (
                  <div className="text-center py-12">
                    <Filter className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      No smart lists yet
                    </h3>
                    <p className="text-sm text-gray-600 mb-6">
                      Create smart lists to automatically segment your properties
                    </p>
                    <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors inline-flex items-center space-x-2">
                      <Plus className="h-4 w-4" />
                      <span>Create Smart List</span>
                    </button>
                  </div>
                ) : (
                  smartLists.map((list) => (
                    <div
                      key={list.id}
                      className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors cursor-pointer"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="text-sm font-semibold text-gray-900">{list.name}</h3>
                            <span className="flex items-center text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded">
                              <TrendingUp className="h-3 w-3 mr-1" />
                              {list.property_count} properties
                            </span>
                          </div>
                          {list.description && (
                            <p className="text-sm text-gray-600 mb-3">{list.description}</p>
                          )}
                          <div className="flex items-center space-x-2">
                            {list.tags.map((tag) => (
                              <span
                                key={tag}
                                className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                          <div className="mt-3 pt-3 border-t border-gray-100">
                            <p className="text-xs text-gray-500">
                              {list.filters.length} filter{list.filters.length !== 1 ? 's' : ''} •
                              Updated {format(new Date(list.updated_at), 'MMM d, yyyy')}
                            </p>
                          </div>
                        </div>
                        <button className="ml-4 p-2 hover:bg-gray-100 rounded transition-colors">
                          <ChevronRight className="h-5 w-5 text-gray-400" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
