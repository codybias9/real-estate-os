'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/store/authStore'

/**
 * AuthHydration component
 *
 * Handles client-side hydration of the auth store from localStorage.
 * This prevents hydration mismatches by only rehydrating after the
 * component mounts on the client.
 *
 * Usage: Add this component to your root layout
 */
export function AuthHydration() {
  useEffect(() => {
    // Manually trigger hydration from localStorage after client mount
    useAuthStore.persist.rehydrate()
  }, [])

  return null
}
