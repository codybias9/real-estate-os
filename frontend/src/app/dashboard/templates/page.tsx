'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import type { Template } from '@/types'
import {
  FileText,
  Mail,
  MessageSquare,
  Plus,
  Edit,
  Trash2,
  BarChart3,
  Clock,
  CheckCircle,
  Eye,
} from 'lucide-react'
import { format } from 'date-fns'

export default function TemplatesPage() {
  const { user } = useAuthStore()
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  useEffect(() => {
    fetchTemplates()
  }, [user?.team_id])

  const fetchTemplates = async () => {
    if (!user?.team_id) return

    try {
      setLoading(true)
      const data = await apiClient.templates.list(user.team_id)
      setTemplates(data)
    } catch (error) {
      console.error('Failed to fetch templates:', error)
    } finally {
      setLoading(false)
    }
  }

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'email':
        return <Mail className="h-5 w-5" />
      case 'sms':
        return <MessageSquare className="h-5 w-5" />
      case 'mail':
        return <FileText className="h-5 w-5" />
      default:
        return <FileText className="h-5 w-5" />
    }
  }

  const getChannelColor = (channel: string) => {
    switch (channel) {
      case 'email':
        return 'bg-blue-100 text-blue-700'
      case 'sms':
        return 'bg-green-100 text-green-700'
      case 'mail':
        return 'bg-purple-100 text-purple-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-3xl font-bold text-gray-900">Templates</h1>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Templates</h1>
            <p className="text-gray-600 mt-1">
              Manage your communication templates and track performance
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2">
              <Plus className="h-4 w-4" />
              <span>New Template</span>
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Templates</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{templates.length}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <FileText className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Templates</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {templates.filter((t) => t.is_active).length}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Usage</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {templates.reduce((sum, t) => sum + t.usage_count, 0)}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <BarChart3 className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Success Rate</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {templates.length > 0
                    ? Math.round(
                        (templates.reduce((sum, t) => sum + t.success_rate, 0) /
                          templates.length) *
                          100
                      )
                    : 0}
                  %
                </p>
              </div>
              <div className="p-3 bg-yellow-100 rounded-lg">
                <BarChart3 className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Templates Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.length === 0 ? (
            <div className="col-span-full bg-white rounded-lg shadow-soft p-12 text-center">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No templates yet</h3>
              <p className="text-sm text-gray-600 mb-6">
                Create your first template to start sending personalized communications
              </p>
              <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors inline-flex items-center space-x-2">
                <Plus className="h-4 w-4" />
                <span>Create Template</span>
              </button>
            </div>
          ) : (
            templates.map((template) => (
              <div
                key={template.id}
                className={`bg-white rounded-lg shadow-soft hover:shadow-medium transition-shadow overflow-hidden ${
                  !template.is_active ? 'opacity-60' : ''
                }`}
              >
                {/* Header */}
                <div className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className={`p-2 rounded-lg ${getChannelColor(template.channel)}`}>
                        {getChannelIcon(template.channel)}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">{template.name}</h3>
                        <span className="text-xs text-gray-500 capitalize">{template.channel}</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => setSelectedTemplate(template)}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                      >
                        <Eye className="h-4 w-4 text-gray-600" />
                      </button>
                      <button className="p-1.5 hover:bg-gray-100 rounded transition-colors">
                        <Edit className="h-4 w-4 text-gray-600" />
                      </button>
                    </div>
                  </div>

                  {/* Stages */}
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {template.applicable_stages.slice(0, 3).map((stage) => (
                      <span
                        key={stage}
                        className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                      >
                        {stage}
                      </span>
                    ))}
                    {template.applicable_stages.length > 3 && (
                      <span className="text-xs text-gray-500">
                        +{template.applicable_stages.length - 3}
                      </span>
                    )}
                  </div>

                  {/* Stats */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Usage Count</span>
                      <span className="font-semibold text-gray-900">{template.usage_count}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Success Rate</span>
                      <span className="font-semibold text-gray-900">
                        {Math.round(template.success_rate * 100)}%
                      </span>
                    </div>
                    {template.avg_response_time_hours && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Avg Response</span>
                        <span className="font-semibold text-gray-900">
                          {Math.round(template.avg_response_time_hours)}h
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                      <span>Performance</span>
                      <span>{Math.round(template.success_rate * 100)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          template.success_rate >= 0.7
                            ? 'bg-green-500'
                            : template.success_rate >= 0.4
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${template.success_rate * 100}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-xs text-gray-500">
                    Created {format(new Date(template.created_at), 'MMM d, yyyy')}
                  </span>
                  {template.is_active ? (
                    <span className="text-xs font-medium text-green-600 flex items-center">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Active
                    </span>
                  ) : (
                    <span className="text-xs font-medium text-gray-500">Inactive</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Template Preview Modal */}
        {selectedTemplate && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedTemplate(null)}
          >
            <div
              className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">
                      {selectedTemplate.name}
                    </h2>
                    <p className="text-sm text-gray-600 mt-1 capitalize">
                      {selectedTemplate.channel} template
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedTemplate(null)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <span className="text-gray-500 text-xl">×</span>
                  </button>
                </div>
              </div>

              <div className="p-6 space-y-6">
                {/* Subject (for email) */}
                {selectedTemplate.subject_template && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-2">Subject Line</h3>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-700">{selectedTemplate.subject_template}</p>
                    </div>
                  </div>
                )}

                {/* Body */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">Message Body</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {selectedTemplate.body_template}
                    </p>
                  </div>
                </div>

                {/* Variables */}
                {selectedTemplate.variables && selectedTemplate.variables.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-2">Variables Used</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedTemplate.variables.map((variable) => (
                        <span
                          key={variable}
                          className="text-xs font-mono bg-blue-100 text-blue-700 px-2 py-1 rounded"
                        >
                          {variable}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Applicable Stages */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">Applicable Stages</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedTemplate.applicable_stages.map((stage) => (
                      <span
                        key={stage}
                        className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
                      >
                        {stage}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="p-6 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
                <button
                  onClick={() => setSelectedTemplate(null)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Close
                </button>
                <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2">
                  <Edit className="h-4 w-4" />
                  <span>Edit Template</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
