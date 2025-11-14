import { useState, useCallback } from 'react'
import type { ToastProps } from '@/components/Toast'

let toastId = 0

export function useToast() {
  const [toasts, setToasts] = useState<ToastProps[]>([])

  const addToast = useCallback((toast: Omit<ToastProps, 'id' | 'onClose'>) => {
    const id = `toast-${toastId++}`
    setToasts((prev) => [...prev, { ...toast, id, onClose: () => {} }])
    return id
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [])

  const showSuccess = useCallback(
    (title: string, message?: string) => {
      return addToast({ title, message, type: 'success' })
    },
    [addToast]
  )

  const showError = useCallback(
    (title: string, message?: string) => {
      return addToast({ title, message, type: 'error' })
    },
    [addToast]
  )

  const showInfo = useCallback(
    (title: string, message?: string) => {
      return addToast({ title, message, type: 'info' })
    },
    [addToast]
  )

  const showEvent = useCallback(
    (title: string, message?: string) => {
      return addToast({ title, message, type: 'event', duration: 3000 })
    },
    [addToast]
  )

  return {
    toasts,
    addToast,
    removeToast,
    showSuccess,
    showError,
    showInfo,
    showEvent,
  }
}
