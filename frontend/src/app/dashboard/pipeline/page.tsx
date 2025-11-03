'use client'

import { useEffect, useState } from 'react'
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd'
import DashboardLayout from '@/components/DashboardLayout'
import PropertyDrawer from '@/components/PropertyDrawer'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import { useSSE } from '@/hooks/useSSE'
import type { Property, PropertyStage } from '@/types'
import { Building2, MapPin, Calendar, User, Wifi, WifiOff } from 'lucide-react'
import { format } from 'date-fns'

interface PipelineColumn {
  id: PropertyStage
  title: string
  dotColor: string
  bgColor: string
  properties: Property[]
}

const PIPELINE_COLUMNS: Array<{ id: PropertyStage; title: string; dotColor: string; bgColor: string }> = [
  { id: 'new', title: 'New', dotColor: 'bg-blue-600', bgColor: 'bg-blue-50' },
  { id: 'outreach', title: 'Outreach', dotColor: 'bg-yellow-600', bgColor: 'bg-yellow-50' },
  { id: 'qualified', title: 'Qualified', dotColor: 'bg-green-600', bgColor: 'bg-green-50' },
  { id: 'negotiation', title: 'Negotiation', dotColor: 'bg-purple-600', bgColor: 'bg-purple-50' },
  { id: 'under_contract', title: 'Under Contract', dotColor: 'bg-indigo-600', bgColor: 'bg-indigo-50' },
  { id: 'closed_won', title: 'Closed Won', dotColor: 'bg-green-700', bgColor: 'bg-green-100' },
  { id: 'closed_lost', title: 'Closed Lost', dotColor: 'bg-gray-600', bgColor: 'bg-gray-50' },
]

export default function PipelinePage() {
  const { user } = useAuthStore()
  const [columns, setColumns] = useState<PipelineColumn[]>([])
  const [loading, setLoading] = useState(true)
  const [draggingPropertyId, setDraggingPropertyId] = useState<number | null>(null)
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  // Real-time updates via SSE
  const { isConnected: sseConnected } = useSSE(user?.team_id, {
    onPropertyUpdated: (data) => {
      console.log('Property updated via SSE:', data)
      // Refresh properties to get the latest data
      fetchProperties()
    },
    onMemoGenerated: (data) => {
      console.log('Memo generated via SSE:', data)
      fetchProperties()
    },
    onConnected: () => {
      console.log('SSE connected - real-time updates enabled')
    },
    onDisconnected: () => {
      console.log('SSE disconnected')
    },
  })

  useEffect(() => {
    fetchProperties()
  }, [user?.team_id])

  const fetchProperties = async () => {
    if (!user?.team_id) return

    try {
      setLoading(true)
      const properties = await apiClient.properties.list({ team_id: user.team_id })

      // Group properties by stage
      const columnData: PipelineColumn[] = PIPELINE_COLUMNS.map((col) => ({
        ...col,
        properties: properties.filter((p: Property) => p.current_stage === col.id),
      }))

      setColumns(columnData)
    } catch (error) {
      console.error('Failed to fetch properties:', error)
    } finally {
      setLoading(false)
    }
  }

  const openPropertyDrawer = (propertyId: number) => {
    setSelectedPropertyId(propertyId)
    setIsDrawerOpen(true)
  }

  const closePropertyDrawer = () => {
    setIsDrawerOpen(false)
    // Refresh properties when drawer closes to get any updates
    fetchProperties()
  }

  const handleDragStart = (result: any) => {
    setDraggingPropertyId(parseInt(result.draggableId.split('-')[1]))
  }

  const handleDragEnd = async (result: DropResult) => {
    setDraggingPropertyId(null)

    if (!result.destination) return

    const sourceStage = result.source.droppableId as PropertyStage
    const destStage = result.destination.droppableId as PropertyStage

    if (sourceStage === destStage) return

    const propertyId = parseInt(result.draggableId.split('-')[1])

    // Optimistic update
    const newColumns = columns.map((col) => {
      if (col.id === sourceStage) {
        return {
          ...col,
          properties: col.properties.filter((p) => p.id !== propertyId),
        }
      }
      if (col.id === destStage) {
        const movedProperty = columns
          .find((c) => c.id === sourceStage)
          ?.properties.find((p) => p.id === propertyId)

        if (movedProperty) {
          return {
            ...col,
            properties: [...col.properties, { ...movedProperty, current_stage: destStage }],
          }
        }
      }
      return col
    })

    setColumns(newColumns)

    // Update backend
    try {
      await apiClient.properties.update(propertyId, {
        current_stage: destStage,
      })
    } catch (error) {
      console.error('Failed to update property stage:', error)
      // Revert on error
      fetchProperties()
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-3xl font-bold text-gray-900">Pipeline</h1>
          <div className="flex space-x-4 overflow-x-auto pb-6">
            {PIPELINE_COLUMNS.map((col) => (
              <div
                key={col.id}
                className="flex-shrink-0 w-80 bg-white rounded-lg shadow-soft p-4 animate-pulse"
              >
                <div className="h-6 bg-gray-200 rounded w-1/2 mb-4" />
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-32 bg-gray-100 rounded" />
                  ))}
                </div>
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
            <h1 className="text-3xl font-bold text-gray-900">Pipeline</h1>
            <p className="text-gray-600 mt-1">
              Manage your deal flow across all stages
            </p>
          </div>
          <div className="flex items-center space-x-4">
            {/* SSE Connection Status */}
            <div
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium ${
                sseConnected
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {sseConnected ? (
                <>
                  <Wifi className="h-3 w-3" />
                  <span>Live Updates</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-3 w-3" />
                  <span>Offline</span>
                </>
              )}
            </div>

            {/* Property Count */}
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <Building2 className="h-4 w-4" />
              <span>
                {columns.reduce((sum, col) => sum + col.properties.length, 0)} properties
              </span>
            </div>
          </div>
        </div>

        {/* Kanban Board */}
        <DragDropContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          <div className="flex space-x-4 overflow-x-auto pb-6">
            {columns.map((column) => (
              <Droppable key={column.id} droppableId={column.id}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`flex-shrink-0 w-80 ${column.bgColor} rounded-lg p-4 transition-colors ${
                      snapshot.isDraggingOver ? 'ring-2 ring-primary-500' : ''
                    }`}
                  >
                    {/* Column Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-2">
                        <div className={`w-3 h-3 rounded-full ${column.dotColor}`} />
                        <h3 className="font-semibold text-gray-900">{column.title}</h3>
                      </div>
                      <span className="text-sm font-medium text-gray-600 bg-white px-2 py-1 rounded">
                        {column.properties.length}
                      </span>
                    </div>

                    {/* Property Cards */}
                    <div className="space-y-3 min-h-[200px]">
                      {column.properties.map((property, index) => (
                        <Draggable
                          key={property.id}
                          draggableId={`property-${property.id}`}
                          index={index}
                        >
                          {(provided, snapshot) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              onClick={() => openPropertyDrawer(property.id)}
                              className={`bg-white rounded-lg shadow-sm p-4 cursor-pointer hover:shadow-md transition-shadow ${
                                snapshot.isDragging ? 'shadow-lg ring-2 ring-primary-500' : ''
                              }`}
                            >
                              {/* Property Address */}
                              <div className="flex items-start justify-between mb-3">
                                <div className="flex-1">
                                  <h4 className="font-semibold text-gray-900 text-sm leading-tight">
                                    {property.address}
                                  </h4>
                                  <div className="flex items-center text-xs text-gray-500 mt-1">
                                    <MapPin className="h-3 w-3 mr-1" />
                                    {property.city}, {property.state} {property.zip_code}
                                  </div>
                                </div>
                              </div>

                              {/* Property Details */}
                              <div className="space-y-2">
                                {/* Owner */}
                                {property.owner_name && (
                                  <div className="flex items-center text-xs text-gray-600">
                                    <User className="h-3 w-3 mr-1.5" />
                                    {property.owner_name}
                                  </div>
                                )}

                                {/* Bird Dog Score */}
                                <div className="flex items-center text-xs">
                                  <span className="font-medium text-gray-600 mr-2">Score:</span>
                                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                                    <div
                                      className={`h-2 rounded-full ${
                                        property.bird_dog_score >= 0.7
                                          ? 'bg-green-500'
                                          : property.bird_dog_score >= 0.4
                                          ? 'bg-yellow-500'
                                          : 'bg-red-500'
                                      }`}
                                      style={{ width: `${property.bird_dog_score * 100}%` }}
                                    />
                                  </div>
                                  <span className="ml-2 text-gray-700 font-medium">
                                    {Math.round(property.bird_dog_score * 100)}
                                  </span>
                                </div>

                                {/* Last Contact */}
                                {property.last_contact_at && (
                                  <div className="flex items-center text-xs text-gray-500">
                                    <Calendar className="h-3 w-3 mr-1.5" />
                                    Last contact: {format(new Date(property.last_contact_at), 'MMM d')}
                                  </div>
                                )}
                              </div>

                              {/* Tags */}
                              {property.tags && property.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-3">
                                  {property.tags.slice(0, 2).map((tag) => (
                                    <span
                                      key={tag}
                                      className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                  {property.tags.length > 2 && (
                                    <span className="text-xs text-gray-500">
                                      +{property.tags.length - 2}
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  </div>
                )}
              </Droppable>
            ))}
          </div>
        </DragDropContext>

        {/* Property Drawer */}
        <PropertyDrawer
          propertyId={selectedPropertyId}
          isOpen={isDrawerOpen}
          onClose={closePropertyDrawer}
        />
      </div>
    </DashboardLayout>
  )
}
