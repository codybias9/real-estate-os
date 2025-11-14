'use client'

import { useEffect, useState } from 'react'

/**
 * ClientOnly component
 *
 * Prevents hydration mismatches by only rendering children on the client.
 * Use this to wrap any component that accesses browser-only APIs like
 * localStorage, window, or uses Zustand stores with persist middleware.
 *
 * Usage:
 * ```tsx
 * <ClientOnly fallback={<Loading />}>
 *   <ComponentThatUsesLocalStorage />
 * </ClientOnly>
 * ```
 */
export function ClientOnly({
  children,
  fallback = null,
}: {
  children: React.ReactNode
  fallback?: React.ReactNode
}) {
  const [hasMounted, setHasMounted] = useState(false)

  useEffect(() => {
    setHasMounted(true)
  }, [])

  if (!hasMounted) {
    return <>{fallback}</>
  }

  return <>{children}</>
}
