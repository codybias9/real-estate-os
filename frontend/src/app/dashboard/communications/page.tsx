'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import type { Property, Template, Communication } from '@/types'
import {
  Send,
  Mail,
  FileText,
  Search,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader,
} from 'lucide-react'
import { format } from 'date-fns'

export default function CommunicationsPage() {
  const { user } = useAuthStore()
  const [properties, setProperties] = useState<Property[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [recentCommunications, setRecentCommunications] = useState<Communication[]>([])
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    fetchData()
  }, [user?.team_id])

  const fetchData = async () => {
    if (!user?.team_id) return

    try {
      setLoading(true)

      // Fetch properties needing contact
      const propertiesData = await apiClient.properties.list({
        team_id: user.team_id,
        limit: 50,
      })
      setProperties(propertiesData)

      // Fetch templates
      const templatesData = await apiClient.templates.list(user.team_id)
      setTemplates(templatesData)
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateAndSend = async () => {
    if (!selectedProperty || !selectedTemplate) return

    try {
      setSending(true)
      setErrorMessage('')
      setSuccessMessage('')

      const response = await apiClient.quickWins.generateAndSend(
        selectedProperty.id,
        selectedTemplate.id
      )

      setSuccessMessage(
        `Memo generated and sent successfully to ${selectedProperty.address}!`
      )

      // Refresh data
      fetchData()

      // Clear selection after 2 seconds
      setTimeout(() => {
        setSelectedProperty(null)
        setSelectedTemplate(null)
        setSuccessMessage('')
      }, 3000)
    } catch (error: any) {
      console.error('Failed to generate and send:', error)
      setErrorMessage(
        error.response?.data?.detail?.error || 'Failed to generate and send memo'
      )
    } finally {
      setSending(false)
    }
  }

  const filteredProperties = properties.filter(
    (p) =>
      p.address.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.owner_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.city.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'delivered':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'sent':
        return <CheckCircle className="h-4 w-4 text-blue-500" />
      case 'queued':
        return <Clock className="h-4 w-4 text-yellow-500" />
      case 'failed':
      case 'bounced':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-3xl font-bold text-gray-900">Communications</h1>
          <div className="animate-pulse space-y-4">
            <div className="h-48 bg-gray-200 rounded-lg" />
            <div className="h-48 bg-gray-200 rounded-lg" />
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
          <h1 className="text-3xl font-bold text-gray-900">Communications</h1>
          <p className="text-gray-600 mt-1">Generate and send personalized memos to property owners</p>
        </div>

        {/* Success/Error Messages */}
        {successMessage && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center">
            <CheckCircle className="h-5 w-5 text-green-600 mr-3" />
            <p className="text-sm text-green-800">{successMessage}</p>
          </div>
        )}

        {errorMessage && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center">
            <AlertCircle className="h-5 w-5 text-red-600 mr-3" />
            <p className="text-sm text-red-800">{errorMessage}</p>
          </div>
        )}

        {/* Generate and Send Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Property Selection */}
          <div className="bg-white rounded-lg shadow-soft p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Property</h2>

            {/* Search */}
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search properties..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            {/* Properties List */}
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {filteredProperties.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">No properties found</p>
              ) : (
                filteredProperties.map((property) => (
                  <button
                    key={property.id}
                    onClick={() => setSelectedProperty(property)}
                    className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                      selectedProperty?.id === property.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300 bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900 text-sm">{property.address}</p>
                        <p className="text-xs text-gray-600 mt-1">
                          {property.city}, {property.state}
                        </p>
                        {property.owner_name && (
                          <p className="text-xs text-gray-500 mt-1">Owner: {property.owner_name}</p>
                        )}
                      </div>
                      <div className="ml-3">
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            property.current_stage === 'new'
                              ? 'bg-blue-100 text-blue-700'
                              : property.current_stage === 'outreach'
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-green-100 text-green-700'
                          }`}
                        >
                          {property.current_stage}
                        </span>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Template Selection and Send */}
          <div className="space-y-6">
            {/* Template Selection */}
            <div className="bg-white rounded-lg shadow-soft p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Template</h2>

              <div className="space-y-2">
                {templates.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-8">
                    No templates available
                  </p>
                ) : (
                  templates
                    .filter((t) => t.is_active)
                    .map((template) => (
                      <button
                        key={template.id}
                        onClick={() => setSelectedTemplate(template)}
                        className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                          selectedTemplate?.id === template.id
                            ? 'border-primary-500 bg-primary-50'
                            : 'border-gray-200 hover:border-gray-300 bg-white'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2">
                              <FileText className="h-4 w-4 text-gray-500" />
                              <p className="font-semibold text-gray-900 text-sm">
                                {template.name}
                              </p>
                            </div>
                            <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                              <span>Used {template.usage_count} times</span>
                              <span>
                                {Math.round(template.success_rate * 100)}% success rate
                              </span>
                            </div>
                          </div>
                        </div>
                      </button>
                    ))
                )}
              </div>
            </div>

            {/* Send Button */}
            <div className="bg-gradient-to-br from-primary-50 to-secondary-50 rounded-lg p-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Ready to Send?</h3>

              {selectedProperty && selectedTemplate ? (
                <>
                  <div className="bg-white rounded-lg p-4 mb-4">
                    <p className="text-sm text-gray-700 mb-2">
                      <strong>Property:</strong> {selectedProperty.address}
                    </p>
                    <p className="text-sm text-gray-700">
                      <strong>Template:</strong> {selectedTemplate.name}
                    </p>
                  </div>

                  <button
                    onClick={handleGenerateAndSend}
                    disabled={sending}
                    className="w-full bg-primary-600 text-white py-3 px-4 rounded-lg hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
                  >
                    {sending ? (
                      <>
                        <Loader className="h-5 w-5 animate-spin" />
                        <span>Generating and Sending...</span>
                      </>
                    ) : (
                      <>
                        <Send className="h-5 w-5" />
                        <span>Generate & Send Memo</span>
                      </>
                    )}
                  </button>
                </>
              ) : (
                <p className="text-sm text-gray-600 text-center py-4">
                  Select a property and template to continue
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Properties</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{properties.length}</p>
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
                <Mail className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-soft p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Memos with Reply</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {properties.filter((p) => p.memo_generated_at).length}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <CheckCircle className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
