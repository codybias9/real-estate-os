'use client'

import { useEffect, useState, Fragment } from 'react'
import { apiClient } from '@/lib/api'
import type { Property, TimelineEvent, Communication, Task } from '@/types'
import {
  X,
  MapPin,
  User,
  Calendar,
  Mail,
  Phone,
  FileText,
  Clock,
  CheckCircle,
  TrendingUp,
  Building2,
  Tag,
  ExternalLink,
  AlertTriangle,
  Zap,
  Database,
  Shield,
} from 'lucide-react'
import { format } from 'date-fns'

interface PropertyDrawerProps {
  propertyId: number | null
  isOpen: boolean
  onClose: () => void
}

export default function PropertyDrawer({ propertyId, isOpen, onClose }: PropertyDrawerProps) {
  const [property, setProperty] = useState<Property | null>(null)
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [communications, setCommunications] = useState<Communication[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [signals, setSignals] = useState<any[]>([])
  const [provenance, setProvenance] = useState<any | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline' | 'communications' | 'signals' | 'provenance'>('overview')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (propertyId && isOpen) {
      fetchPropertyData()
    }
  }, [propertyId, isOpen])

  const fetchPropertyData = async () => {
    if (!propertyId) return

    try {
      setLoading(true)

      // Fetch property details
      const propertyData = await apiClient.properties.get(propertyId)
      setProperty(propertyData)

      // Fetch timeline
      const timelineData = await apiClient.properties.getTimeline(propertyId)
      setTimeline(timelineData)

      // Fetch communications
      const commsData = await apiClient.communications.list(propertyId)
      setCommunications(commsData)

      // Fetch tasks
      const tasksData = await apiClient.tasks.list(propertyId)
      setTasks(tasksData)

      // Fetch data signals (property ID as string)
      try {
        const signalsData = await apiClient.dataPropensity.getSignals(propertyId.toString())
        setSignals(signalsData)
      } catch (error) {
        console.error('Failed to fetch signals:', error)
        setSignals([])
      }

      // Fetch provenance
      try {
        const provenanceData = await apiClient.dataPropensity.getProvenance(propertyId.toString())
        setProvenance(provenanceData)
      } catch (error) {
        console.error('Failed to fetch provenance:', error)
        setProvenance(null)
      }
    } catch (error) {
      console.error('Failed to fetch property data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen || !property) return null

  const getStageColor = (stage: string) => {
    const colors: Record<string, string> = {
      new: 'bg-blue-100 text-blue-700',
      outreach: 'bg-yellow-100 text-yellow-700',
      qualified: 'bg-green-100 text-green-700',
      negotiation: 'bg-purple-100 text-purple-700',
      under_contract: 'bg-indigo-100 text-indigo-700',
      closed_won: 'bg-green-200 text-green-800',
      closed_lost: 'bg-gray-100 text-gray-700',
    }
    return colors[stage] || 'bg-gray-100 text-gray-700'
  }

  const getEventIcon = (eventType: string) => {
    const icons: Record<string, any> = {
      property_created: Building2,
      stage_changed: TrendingUp,
      memo_generated: FileText,
      communication_sent: Mail,
      communication_received: Mail,
      task_created: CheckCircle,
      task_completed: CheckCircle,
      note_added: FileText,
    }
    const Icon = icons[eventType] || Clock
    return <Icon className="h-4 w-4" />
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black bg-opacity-50 transition-opacity z-40 ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={`fixed right-0 top-0 h-full w-full md:w-[600px] bg-white shadow-2xl transform transition-transform duration-300 ease-in-out z-50 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
          </div>
        ) : (
          <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-start justify-between p-6 border-b border-gray-200">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <h2 className="text-2xl font-bold text-gray-900">{property.address}</h2>
                  <button
                    onClick={onClose}
                    className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <X className="h-5 w-5 text-gray-500" />
                  </button>
                </div>
                <div className="flex items-center text-sm text-gray-600">
                  <MapPin className="h-4 w-4 mr-1" />
                  {property.city}, {property.state} {property.zip_code}
                </div>
                <div className="flex items-center space-x-2 mt-3">
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-full ${getStageColor(
                      property.current_stage
                    )}`}
                  >
                    {property.current_stage.replace('_', ' ').toUpperCase()}
                  </span>
                  <div className="flex items-center space-x-1 text-sm text-gray-600">
                    <TrendingUp className="h-4 w-4" />
                    <span>Score: {Math.round(property.bird_dog_score * 100)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-200 px-6 overflow-x-auto">
              <button
                onClick={() => setActiveTab('overview')}
                className={`py-3 px-4 font-medium text-sm border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === 'overview'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab('timeline')}
                className={`py-3 px-4 font-medium text-sm border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === 'timeline'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Timeline
              </button>
              <button
                onClick={() => setActiveTab('communications')}
                className={`py-3 px-4 font-medium text-sm border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === 'communications'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Communications ({communications.length})
              </button>
              <button
                onClick={() => setActiveTab('signals')}
                className={`py-3 px-4 font-medium text-sm border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === 'signals'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Data Signals ({signals.length})
              </button>
              <button
                onClick={() => setActiveTab('provenance')}
                className={`py-3 px-4 font-medium text-sm border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === 'provenance'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Provenance
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {/* Property Details */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-3">Property Details</h3>
                    <div className="space-y-3">
                      {property.owner_name && (
                        <div className="flex items-start">
                          <User className="h-4 w-4 text-gray-400 mt-0.5 mr-3" />
                          <div>
                            <p className="text-sm font-medium text-gray-700">Owner</p>
                            <p className="text-sm text-gray-900">{property.owner_name}</p>
                          </div>
                        </div>
                      )}
                      {property.apn && (
                        <div className="flex items-start">
                          <FileText className="h-4 w-4 text-gray-400 mt-0.5 mr-3" />
                          <div>
                            <p className="text-sm font-medium text-gray-700">APN</p>
                            <p className="text-sm text-gray-900 font-mono">{property.apn}</p>
                          </div>
                        </div>
                      )}
                      {property.last_contact_at && (
                        <div className="flex items-start">
                          <Calendar className="h-4 w-4 text-gray-400 mt-0.5 mr-3" />
                          <div>
                            <p className="text-sm font-medium text-gray-700">Last Contact</p>
                            <p className="text-sm text-gray-900">
                              {format(new Date(property.last_contact_at), 'MMM d, yyyy')}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Tags */}
                  {property.tags && property.tags.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">Tags</h3>
                      <div className="flex flex-wrap gap-2">
                        {property.tags.map((tag) => (
                          <span
                            key={tag}
                            className="inline-flex items-center text-sm bg-gray-100 text-gray-700 px-3 py-1 rounded-full"
                          >
                            <Tag className="h-3 w-3 mr-1" />
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {property.notes && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">Notes</h3>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{property.notes}</p>
                      </div>
                    </div>
                  )}

                  {/* Memo */}
                  {property.memo_content && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">Generated Memo</h3>
                      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {property.memo_content}
                        </p>
                        {property.memo_generated_at && (
                          <p className="text-xs text-gray-500 mt-3">
                            Generated {format(new Date(property.memo_generated_at), 'MMM d, yyyy')}
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Open Tasks */}
                  {tasks.filter((t) => t.status !== 'completed' && t.status !== 'cancelled').length >
                    0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">Open Tasks</h3>
                      <div className="space-y-2">
                        {tasks
                          .filter((t) => t.status !== 'completed' && t.status !== 'cancelled')
                          .map((task) => (
                            <div key={task.id} className="flex items-start bg-gray-50 rounded-lg p-3">
                              <CheckCircle className="h-4 w-4 text-gray-400 mt-0.5 mr-3 flex-shrink-0" />
                              <div className="flex-1">
                                <p className="text-sm font-medium text-gray-900">{task.title}</p>
                                {task.due_date && (
                                  <p className="text-xs text-gray-500 mt-1">
                                    Due: {format(new Date(task.due_date), 'MMM d, yyyy')}
                                  </p>
                                )}
                              </div>
                              <span
                                className={`text-xs px-2 py-0.5 rounded ${
                                  task.priority === 'urgent'
                                    ? 'bg-red-100 text-red-700'
                                    : task.priority === 'high'
                                    ? 'bg-orange-100 text-orange-700'
                                    : 'bg-gray-100 text-gray-700'
                                }`}
                              >
                                {task.priority}
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'timeline' && (
                <div className="space-y-4">
                  {timeline.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-8">No timeline events yet</p>
                  ) : (
                    <div className="relative">
                      {/* Timeline line */}
                      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

                      {/* Events */}
                      {timeline.map((event, index) => (
                        <div key={event.id} className="relative flex items-start mb-6 last:mb-0">
                          {/* Icon */}
                          <div className="relative z-10 flex items-center justify-center w-8 h-8 bg-white border-2 border-primary-500 rounded-full">
                            {getEventIcon(event.event_type)}
                          </div>

                          {/* Content */}
                          <div className="ml-4 flex-1">
                            <div className="bg-white border border-gray-200 rounded-lg p-4">
                              <h4 className="text-sm font-semibold text-gray-900">
                                {event.event_title}
                              </h4>
                              <p className="text-sm text-gray-600 mt-1">{event.event_description}</p>
                              <p className="text-xs text-gray-500 mt-2">
                                {format(new Date(event.created_at), 'MMM d, yyyy h:mm a')}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'communications' && (
                <div className="space-y-4">
                  {communications.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-8">
                      No communications yet
                    </p>
                  ) : (
                    communications.map((comm) => (
                      <div
                        key={comm.id}
                        className={`border rounded-lg p-4 ${
                          comm.direction === 'inbound'
                            ? 'bg-blue-50 border-blue-200'
                            : 'bg-gray-50 border-gray-200'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            {comm.channel === 'email' ? (
                              <Mail className="h-4 w-4 text-gray-500" />
                            ) : comm.channel === 'sms' ? (
                              <Phone className="h-4 w-4 text-gray-500" />
                            ) : (
                              <Phone className="h-4 w-4 text-gray-500" />
                            )}
                            <span className="text-xs font-medium text-gray-700">
                              {comm.direction === 'inbound' ? 'Received' : 'Sent'}
                            </span>
                          </div>
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${
                              comm.status === 'delivered'
                                ? 'bg-green-100 text-green-700'
                                : comm.status === 'sent'
                                ? 'bg-blue-100 text-blue-700'
                                : comm.status === 'failed'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {comm.status}
                          </span>
                        </div>

                        {comm.subject && (
                          <h4 className="text-sm font-semibold text-gray-900 mb-1">
                            {comm.subject}
                          </h4>
                        )}

                        <p className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-3">
                          {comm.content}
                        </p>

                        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200">
                          <p className="text-xs text-gray-500">
                            {format(new Date(comm.created_at), 'MMM d, yyyy h:mm a')}
                          </p>
                          <div className="flex items-center text-xs text-gray-500">
                            <span className="mr-1">
                              {comm.direction === 'inbound' ? comm.from_address : comm.to_address}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'signals' && (
                <div className="space-y-4">
                  {signals.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-8">No data signals detected yet</p>
                  ) : (
                    signals.map((signal) => {
                      const getSignalIcon = (type: string) => {
                        switch (type) {
                          case 'distress':
                            return <AlertTriangle className="h-5 w-5" />
                          case 'motivation':
                            return <Zap className="h-5 w-5" />
                          case 'equity':
                            return <TrendingUp className="h-5 w-5" />
                          case 'financial':
                            return <Building2 className="h-5 w-5" />
                          default:
                            return <Database className="h-5 w-5" />
                        }
                      }

                      const getStrengthColor = (strength: string) => {
                        switch (strength) {
                          case 'strong':
                            return 'bg-red-100 text-red-700 border-red-200'
                          case 'moderate':
                            return 'bg-yellow-100 text-yellow-700 border-yellow-200'
                          case 'weak':
                            return 'bg-blue-100 text-blue-700 border-blue-200'
                          default:
                            return 'bg-gray-100 text-gray-700 border-gray-200'
                        }
                      }

                      return (
                        <div
                          key={signal.id}
                          className={`border rounded-lg p-4 ${getStrengthColor(signal.strength)}`}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center space-x-3">
                              <div className="flex-shrink-0">
                                {getSignalIcon(signal.signal_type)}
                              </div>
                              <div>
                                <h4 className="text-sm font-semibold">{signal.title}</h4>
                                <p className="text-xs capitalize mt-1">
                                  {signal.signal_type.replace('_', ' ')} • {signal.strength} signal
                                </p>
                              </div>
                            </div>
                            <div className="flex flex-col items-end space-y-1">
                              <span className="text-xs font-medium px-2 py-0.5 bg-white rounded">
                                Impact: {signal.impact_score}/10
                              </span>
                              <span className="text-xs font-medium px-2 py-0.5 bg-white rounded">
                                {Math.round(signal.confidence_score * 100)}% confident
                              </span>
                            </div>
                          </div>
                          <p className="text-sm mt-2">{signal.description}</p>
                          <div className="flex items-center justify-between mt-3 pt-3 border-t border-current border-opacity-20">
                            <p className="text-xs">
                              Source: {signal.data_source.replace('_', ' ')}
                            </p>
                            <p className="text-xs">
                              Detected: {format(new Date(signal.detected_date), 'MMM d, yyyy')}
                            </p>
                          </div>
                          {signal.actionable && (
                            <div className="mt-2 flex items-center text-xs font-medium">
                              <Zap className="h-3 w-3 mr-1" />
                              Actionable - immediate attention recommended
                            </div>
                          )}
                        </div>
                      )
                    })
                  )}
                </div>
              )}

              {activeTab === 'provenance' && (
                <div className="space-y-4">
                  {!provenance || provenance.provenance_records.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-8">
                      No provenance data available
                    </p>
                  ) : (
                    <>
                      {/* Summary */}
                      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                        <h3 className="text-sm font-semibold text-gray-900 mb-3">
                          Data Completeness
                        </h3>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-600">Enriched Fields</span>
                            <span className="font-semibold text-gray-900">
                              {provenance.enriched_fields} / {provenance.total_fields}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-600">Completeness Score</span>
                            <span className="font-semibold text-gray-900">
                              {Math.round(provenance.completeness_score)}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                            <div
                              className="bg-primary-600 h-2 rounded-full transition-all"
                              style={{ width: `${provenance.completeness_score}%` }}
                            />
                          </div>
                          {provenance.last_enrichment && (
                            <p className="text-xs text-gray-500 mt-3">
                              Last enriched: {format(new Date(provenance.last_enrichment), 'MMM d, yyyy')}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Provenance Records */}
                      <div>
                        <h3 className="text-sm font-semibold text-gray-900 mb-3">
                          Data Sources ({provenance.provenance_records.length})
                        </h3>
                        <div className="space-y-2">
                          {provenance.provenance_records.map((record: any, index: number) => {
                            const getConfidenceColor = (confidence: string) => {
                              switch (confidence) {
                                case 'verified':
                                  return 'bg-green-100 text-green-700'
                                case 'high_confidence':
                                  return 'bg-blue-100 text-blue-700'
                                case 'medium_confidence':
                                  return 'bg-yellow-100 text-yellow-700'
                                case 'low_confidence':
                                  return 'bg-orange-100 text-orange-700'
                                default:
                                  return 'bg-gray-100 text-gray-700'
                              }
                            }

                            return (
                              <div
                                key={index}
                                className="bg-white border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors"
                              >
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <div className="flex items-center space-x-2 mb-1">
                                      <Database className="h-3 w-3 text-gray-400" />
                                      <p className="text-sm font-medium text-gray-900">
                                        {record.field_name.replace('_', ' ')}
                                      </p>
                                    </div>
                                    <p className="text-sm text-gray-700 font-mono">
                                      {typeof record.value === 'object'
                                        ? JSON.stringify(record.value)
                                        : record.value}
                                    </p>
                                    <div className="flex items-center space-x-3 mt-2">
                                      <span className="text-xs text-gray-500">
                                        {record.source.replace('_', ' ')}
                                      </span>
                                      {record.source_identifier && (
                                        <span className="text-xs text-gray-500 font-mono">
                                          {record.source_identifier}
                                        </span>
                                      )}
                                      <span className="text-xs text-gray-500">
                                        {format(new Date(record.acquired_date), 'MMM d, yyyy')}
                                      </span>
                                      {record.cost > 0 && (
                                        <span className="text-xs text-gray-500">
                                          ${record.cost.toFixed(2)}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  <span
                                    className={`text-xs px-2 py-0.5 rounded ${getConfidenceColor(
                                      record.confidence
                                    )}`}
                                  >
                                    {record.confidence.replace('_', ' ')}
                                  </span>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
