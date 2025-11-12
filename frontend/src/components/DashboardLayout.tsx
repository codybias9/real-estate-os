'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
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

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, isAuthenticated, logout } = useAuthStore()
  const [isMounted, setIsMounted] = useState(false)

  // Track client-side mount to prevent hydration mismatch
  useEffect(() => {
    setIsMounted(true)
  }, [])

  // Redirect to login if not authenticated
  useEffect(() => {
    if (isMounted && !isAuthenticated) {
      router.push('/auth/login')
    }
  }, [isMounted, isAuthenticated, router])

  const handleLogout = () => {
    logout()
    router.push('/auth/login')
  }

  // Render a minimal loading state until mounted and authenticated
  // This prevents hydration mismatch by always rendering something
  if (!isMounted || !isAuthenticated || !user) {
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
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation Bar */}
      <nav className="bg-white border-b border-gray-200 fixed w-full z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            {/* Logo */}
            <div className="flex items-center">
              <Link href="/dashboard" className="flex items-center">
                <Building2 className="h-8 w-8 text-primary-600" />
                <span className="ml-2 text-xl font-bold text-gray-900">
                  Real Estate OS
                </span>
              </Link>
            </div>

            {/* Right Side - User Menu */}
            <div className="flex items-center space-x-4">
              {/* Notifications */}
              <button className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors">
                <Bell className="h-5 w-5" />
              </button>

              {/* User Info */}
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
                  <p className="text-xs text-gray-500 capitalize">{user.role}</p>
                </div>
                <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                  <span className="text-primary-600 font-semibold">
                    {user.full_name.charAt(0).toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Logout */}
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Side Navigation */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200 pt-16">
        <nav className="mt-5 px-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-600'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon className={`mr-3 h-5 w-5 ${isActive ? 'text-primary-600' : 'text-gray-400'}`} />
                {item.name}
              </Link>
            )
          })}
        </nav>

        {/* Settings at bottom */}
        <div className="absolute bottom-0 w-full px-3 pb-4">
          <Link
            href="/dashboard/settings"
            className={`flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
              pathname === '/dashboard/settings'
                ? 'bg-primary-50 text-primary-600'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <Settings className="mr-3 h-5 w-5 text-gray-400" />
            Settings
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <main className="pl-64 pt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </div>
      </main>
    </div>
  )
}
