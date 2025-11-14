'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { ClientOnly } from '@/components/ClientOnly'
import { useSSE } from '@/hooks/useSSE'
import SSEConnectionBadge from '@/components/SSEConnectionBadge'
import {
  LayoutDashboard,
  Building2,
  Mail,
  BarChart3,
  FileText,
  Settings,
  LogOut,
  Users,
  Bell,
} from 'lucide-react'

interface DashboardLayoutProps {
  children: React.ReactNode
}

function DashboardLayoutContent({ children }: DashboardLayoutProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, isAuthenticated, logout } = useAuthStore()
  const [eventFlash, setEventFlash] = useState(false)

  // Setup SSE connection
  const { isConnected, lastEvent } = useSSE(user?.team_id || null, {
    onEvent: (event) => {
      console.log('[SSE] Event received:', event.type, event.data)
      // Trigger flash animation
      setEventFlash(true)
      setTimeout(() => setEventFlash(false), 100)
    },
    onConnected: () => {
      console.log('[SSE] Connected to real-time event stream')
    },
    onDisconnected: () => {
      console.log('[SSE] Disconnected from event stream')
    },
  })

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/login')
    }
  }, [isAuthenticated, router])

  const handleLogout = () => {
    logout()
    router.push('/auth/login')
  }

  // Show loading if not authenticated (will redirect via useEffect)
  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    )
  }

  const navItems = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: LayoutDashboard,
    },
    {
      name: 'Pipeline',
      href: '/dashboard/pipeline',
      icon: Building2,
    },
    {
      name: 'Portfolio',
      href: '/dashboard/portfolio',
      icon: BarChart3,
    },
    {
      name: 'Communications',
      href: '/dashboard/communications',
      icon: Mail,
    },
    {
      name: 'Templates',
      href: '/dashboard/templates',
      icon: FileText,
    },
    {
      name: 'Team',
      href: '/dashboard/team',
      icon: Users,
    },
    {
      name: 'Settings',
      href: '/dashboard/settings',
      icon: Settings,
    },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-primary-600">Real Estate OS</h1>
            </div>

            {/* User Menu */}
            <div className="flex items-center space-x-4">
              {/* SSE Connection Badge */}
              <SSEConnectionBadge isConnected={isConnected} onEventReceived={eventFlash} />

              <button className="relative p-2 text-gray-400 hover:text-gray-500 transition-colors">
                <Bell className="h-6 w-6" />
                <span className="absolute top-1.5 right-1.5 block h-2 w-2 rounded-full bg-red-500" />
              </button>

              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
                  <p className="text-xs text-gray-500">{user.email}</p>
                </div>

                <button
                  onClick={handleLogout}
                  className="p-2 text-gray-400 hover:text-gray-500 transition-colors"
                  title="Logout"
                >
                  <LogOut className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-gray-200 min-h-[calc(100vh-4rem)]">
          <nav className="px-3 py-6 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <Icon className={`mr-3 h-5 w-5 ${isActive ? 'text-primary-700' : 'text-gray-400'}`} />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-8">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  )
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <ClientOnly
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-gray-400">Loading...</div>
        </div>
      }
    >
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </ClientOnly>
  )
}
