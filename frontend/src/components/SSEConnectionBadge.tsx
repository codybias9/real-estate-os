'use client'

import { useEffect, useState } from 'react'

interface SSEConnectionBadgeProps {
  isConnected: boolean
  onEventReceived?: boolean // Triggers flash animation
}

export default function SSEConnectionBadge({ isConnected, onEventReceived }: SSEConnectionBadgeProps) {
  const [isFlashing, setIsFlashing] = useState(false)

  // Flash animation when event received
  useEffect(() => {
    if (onEventReceived && isConnected) {
      setIsFlashing(true)
      const timer = setTimeout(() => setIsFlashing(false), 600)
      return () => clearTimeout(timer)
    }
  }, [onEventReceived, isConnected])

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-100 border border-gray-200 text-xs font-medium">
      {/* Connection indicator dot */}
      <div className="relative flex items-center justify-center">
        {/* Outer pulse ring (when flashing) */}
        {isFlashing && (
          <span className="absolute inline-flex h-3 w-3 rounded-full bg-green-400 opacity-75 animate-ping" />
        )}

        {/* Inner dot */}
        <span
          className={`relative inline-flex h-2 w-2 rounded-full transition-colors duration-300 ${
            isConnected
              ? 'bg-green-500'
              : 'bg-gray-400'
          } ${isFlashing ? 'animate-pulse' : ''}`}
        />
      </div>

      {/* Status text */}
      <span className={`transition-colors duration-300 ${
        isConnected ? 'text-green-700' : 'text-gray-600'
      }`}>
        {isConnected ? 'Connected' : 'Live'}
      </span>
    </div>
  )
}
