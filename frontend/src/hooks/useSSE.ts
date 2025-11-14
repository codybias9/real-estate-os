import { useEffect, useRef, useState, useCallback } from 'react'
import { apiClient } from '@/lib/api'

interface SSEEvent {
  type: string
  data: any
  timestamp: string
}

interface UseSSEOptions {
  onEvent?: (event: SSEEvent) => void
  onPropertyUpdated?: (data: any) => void
  onCommunicationSent?: (data: any) => void
  onMemoGenerated?: (data: any) => void
  onTaskCreated?: (data: any) => void
  onTaskCompleted?: (data: any) => void
  onError?: (error: Error) => void
  onConnected?: () => void
  onDisconnected?: () => void
  autoReconnect?: boolean
  reconnectInterval?: number
}

export function useSSE(teamId: number | null | undefined, options: UseSSEOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)

  const {
    onEvent,
    onPropertyUpdated,
    onCommunicationSent,
    onMemoGenerated,
    onTaskCreated,
    onTaskCompleted,
    onError,
    onConnected,
    onDisconnected,
    autoReconnect = true,
    reconnectInterval = 3000,
  } = options

  const handleEvent = useCallback(
    (type: string, data: any) => {
      const event: SSEEvent = {
        type,
        data,
        timestamp: new Date().toISOString(),
      }

      setLastEvent(event)
      onEvent?.(event)

      // Call specific handlers
      switch (type) {
        case 'property_updated':
          onPropertyUpdated?.(data)
          break
        case 'communication_sent':
          onCommunicationSent?.(data)
          break
        case 'memo_generated':
          onMemoGenerated?.(data)
          break
        case 'task_created':
          onTaskCreated?.(data)
          break
        case 'task_completed':
          onTaskCompleted?.(data)
          break
      }
    },
    [onEvent, onPropertyUpdated, onCommunicationSent, onMemoGenerated, onTaskCreated, onTaskCompleted]
  )

  const connect = useCallback(async () => {
    if (!teamId) return

    try {
      // Get SSE token
      const tokenResponse = await apiClient.auth.getCurrentUser() // This ensures we have a valid auth token
      const sseTokenResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/sse/token`,
        {
          headers: {
            Authorization: `Bearer ${
              JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.tokens?.access_token
            }`,
          },
        }
      )

      if (!sseTokenResponse.ok) {
        throw new Error('Failed to get SSE token')
      }

      const { sse_token, stream_url } = await sseTokenResponse.json()

      // Create EventSource connection
      const eventSource = new EventSource(stream_url)

      // Connection opened
      eventSource.onopen = () => {
        console.log('[SSE] Connection established')
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
        onConnected?.()
      }

      // Handle errors
      eventSource.onerror = (err) => {
        console.error('[SSE] Connection error:', err)
        setIsConnected(false)
        eventSource.close()
        eventSourceRef.current = null

        const error = new Error('SSE connection error')
        setError(error)
        onError?.(error)
        onDisconnected?.()

        // Auto-reconnect
        if (autoReconnect && reconnectAttemptsRef.current < 10) {
          reconnectAttemptsRef.current++
          const delay = reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1)
          console.log(`[SSE] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`)

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        }
      }

      // Listen for specific event types
      const eventTypes = [
        'property_updated',
        'communication_sent',
        'memo_generated',
        'task_created',
        'task_completed',
        'stage_changed',
        'data_enriched',
      ]

      eventTypes.forEach((eventType) => {
        eventSource.addEventListener(eventType, (event: MessageEvent) => {
          try {
            const data = JSON.parse(event.data)
            console.log(`[SSE] Received ${eventType}:`, data)
            handleEvent(eventType, data)
          } catch (err) {
            console.error(`[SSE] Failed to parse ${eventType} event:`, err)
          }
        })
      })

      // Store reference
      eventSourceRef.current = eventSource
    } catch (err) {
      console.error('[SSE] Failed to connect:', err)
      const error = err instanceof Error ? err : new Error('Failed to connect to SSE')
      setError(error)
      onError?.(error)

      // Auto-reconnect on failure
      if (autoReconnect && reconnectAttemptsRef.current < 10) {
        reconnectAttemptsRef.current++
        const delay = reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1)
        console.log(`[SSE] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`)

        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, delay)
      }
    }
  }, [teamId, autoReconnect, reconnectInterval, handleEvent, onConnected, onDisconnected, onError])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (eventSourceRef.current) {
      console.log('[SSE] Closing connection')
      eventSourceRef.current.close()
      eventSourceRef.current = null
      setIsConnected(false)
      onDisconnected?.()
    }
  }, [onDisconnected])

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    if (teamId) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [teamId]) // Only reconnect when teamId changes

  return {
    isConnected,
    lastEvent,
    error,
    connect,
    disconnect,
  }
}

// Hook for listening to specific property updates
export function usePropertySSE(propertyId: number | null, options: UseSSEOptions = {}) {
  const { onPropertyUpdated, ...restOptions } = options

  // Filter events to only include this property
  const filteredOnPropertyUpdated = useCallback(
    (data: any) => {
      if (data.property_id === propertyId) {
        onPropertyUpdated?.(data)
      }
    },
    [propertyId, onPropertyUpdated]
  )

  return useSSE(null, {
    ...restOptions,
    onPropertyUpdated: filteredOnPropertyUpdated,
  })
}
