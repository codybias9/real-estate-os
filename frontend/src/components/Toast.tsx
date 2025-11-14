'use client'

import { useEffect } from 'react'
import { X, CheckCircle, AlertCircle, Info, Zap } from 'lucide-react'

export interface ToastProps {
  id?: string
  title: string
  message?: string
  type?: 'success' | 'error' | 'info' | 'event'
  duration?: number
  onClose: () => void
}

export default function Toast({ title, message, type = 'info', duration = 4000, onClose }: ToastProps) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onClose, duration)
      return () => clearTimeout(timer)
    }
  }, [duration, onClose])

  const icons = {
    success: CheckCircle,
    error: AlertCircle,
    info: Info,
    event: Zap,
  }

  const colors = {
    success: 'bg-green-50 border-green-200 text-green-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    event: 'bg-purple-50 border-purple-200 text-purple-800',
  }

  const iconColors = {
    success: 'text-green-500',
    error: 'text-red-500',
    info: 'text-blue-500',
    event: 'text-purple-500',
  }

  const Icon = icons[type]

  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-lg border shadow-lg transition-all duration-300 animate-slide-in ${colors[type]}`}
      style={{
        animation: 'slideIn 0.3s ease-out',
      }}
    >
      <Icon className={`h-5 w-5 flex-shrink-0 ${iconColors[type]}`} />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold">{title}</p>
        {message && <p className="text-xs mt-1 opacity-90">{message}</p>}
      </div>

      <button
        onClick={onClose}
        className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

// Toast Container Component
interface ToastContainerProps {
  toasts: ToastProps[]
  onRemove: (id: string) => void
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
      <div className="space-y-2 pointer-events-auto">
        {toasts.map((toast, index) => (
          <Toast
            key={toast.id || index}
            {...toast}
            onClose={() => onRemove(toast.id || index.toString())}
          />
        ))}
      </div>

      <style jsx global>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  )
}
