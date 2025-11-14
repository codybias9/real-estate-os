'use client'

import { useEffect, useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { ToastContainer } from '@/components/Toast'
import { useSSE } from '@/hooks/useSSE'
import {
  Settings,
  Activity,
  HardDrive,
  Cpu,
  Users,
  Shield,
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Server,
  Database,
  TrendingUp,
  AlertCircle,
  Zap,
} from 'lucide-react'
import { format } from 'date-fns'

interface ServiceHealth {
  service_name: string
  status: 'healthy' | 'degraded' | 'down'
  uptime: number
  last_check: string
  message: string | null
}

interface SystemMetrics {
  total_cpu_usage: number
  total_memory_usage: number
  total_disk_usage: number
  active_workers: number
  total_workers: number
  tasks_queued: number
  tasks_running: number
  error_rate_24h: number
  average_task_duration: number
}

interface WorkerInfo {
  worker_id: string
  hostname: string
  status: 'active' | 'idle' | 'busy'
  tasks_running: number
  tasks_completed: number
  cpu_usage: number
  memory_usage: number
  last_heartbeat: string
}

interface QueueInfo {
  queue_name: string
  tasks_pending: number
  tasks_running: number
  tasks_completed_24h: number
  average_wait_time: number
}

interface StorageInfo {
  storage_type: string
  status: string
  total_size: number | null
  used_size: number | null
  available_size: number | null
  usage_percentage: number | null
}

interface LogEntry {
  timestamp: string
  level: string
  component: string
  message: string
}

export default function AdminPage() {
  const { user } = useAuthStore()
  const [activeTab, setActiveTab] = useState<'system' | 'team' | 'users'>('system')
  const [loading, setLoading] = useState(true)
  const [emitting, setEmitting] = useState(false)

  // Toast notifications
  const { toasts, removeToast, showEvent, showSuccess, showError } = useToast()

  // System state
  const [services, setServices] = useState<ServiceHealth[]>([])
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [workers, setWorkers] = useState<WorkerInfo[]>([])
  const [queues, setQueues] = useState<QueueInfo[]>([])
  const [storage, setStorage] = useState<StorageInfo[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])

  // Listen to SSE events and show toasts
  useSSE(user?.team_id || null, {
    onEvent: (event) => {
      console.log('[Admin] SSE Event received:', event)
      showEvent(
        `Event: ${event.type}`,
        `ID: ${event.data.id || 'N/A'} • ${new Date(event.timestamp).toLocaleTimeString()}`
      )
    },
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [healthData, metricsData, workersData, queuesData, storageData, logsData] =
        await Promise.all([
          apiClient.system.getHealth(),
          apiClient.system.getMetrics(),
          apiClient.system.getWorkers(),
          apiClient.system.getQueues(),
          apiClient.system.getStorage(),
          apiClient.system.getRecentLogs(20),
        ])

      setServices(healthData)
      setMetrics(metricsData)
      setWorkers(workersData)
      setQueues(queuesData)
      setStorage(storageData)
      setLogs(logsData)
    } catch (error) {
      console.error('Failed to fetch admin data:', error)
    } finally {
      setLoading(false)
    }
  }

  const emitTestEvent = async () => {
    try {
      setEmitting(true)
      const eventId = `test-${Date.now()}`

      // Emit a test SSE event via the API
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/sse/test/emit`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            event_type: 'property_updated',
            data: {
              id: eventId,
              property_id: 'demo-property-123',
              message: 'Test event emitted from Admin panel',
              timestamp: new Date().toISOString(),
            },
          }),
        }
      )

      if (response.ok) {
        showSuccess('Test Event Emitted', `Event ID: ${eventId}`)
      } else {
        showError('Failed to emit event', 'SSE test endpoint may not be available')
      }
    } catch (error) {
      console.error('Failed to emit test event:', error)
      showError('Error emitting event', 'Check console for details')
    } finally {
      setEmitting(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'active':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'degraded':
      case 'busy':
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />
      case 'down':
        return <XCircle className="h-5 w-5 text-red-600" />
      default:
        return <Activity className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'active':
        return 'bg-green-100 text-green-700 border-green-200'
      case 'degraded':
      case 'busy':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      case 'down':
        return 'bg-red-100 text-red-700 border-red-200'
      case 'idle':
        return 'bg-blue-100 text-blue-700 border-blue-200'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    return `${days}d ${hours}h`
  }

  const formatBytes = (bytes: number | null) => {
    if (bytes === null) return 'N/A'
    const gb = bytes / (1024 * 1024 * 1024)
    return `${gb.toFixed(1)} GB`
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
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
            <h1 className="text-3xl font-bold text-gray-900">Admin & Settings</h1>
            <p className="text-gray-600 mt-1">
              System health, team management, and configuration
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3">
            <button
              onClick={emitTestEvent}
              disabled={emitting}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Emit a test SSE event to verify real-time connectivity"
            >
              <Zap className={`h-4 w-4 ${emitting ? 'animate-pulse' : ''}`} />
              <span>{emitting ? 'Emitting...' : 'Emit Test Event'}</span>
            </button>

            <button
              onClick={fetchData}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Toast notifications */}
        <ToastContainer toasts={toasts} onRemove={removeToast} />

        {/* System Metrics Overview */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow-soft p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">CPU Usage</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {metrics.total_cpu_usage.toFixed(1)}%
                  </p>
                </div>
                <div className="p-3 bg-blue-100 rounded-lg">
                  <Cpu className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-soft p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Memory</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {metrics.total_memory_usage.toFixed(1)}%
                  </p>
                </div>
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Database className="h-6 w-6 text-purple-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-soft p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Workers</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {metrics.active_workers}/{metrics.total_workers}
                  </p>
                </div>
                <div className="p-3 bg-green-100 rounded-lg">
                  <Server className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-soft p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Error Rate (24h)</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {metrics.error_rate_24h.toFixed(1)}%
                  </p>
                </div>
                <div className="p-3 bg-yellow-100 rounded-lg">
                  <AlertCircle className="h-6 w-6 text-yellow-600" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-soft">
          <div className="border-b border-gray-200">
            <div className="flex">
              <button
                onClick={() => setActiveTab('system')}
                className={`px-6 py-4 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'system'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Activity className="h-4 w-4" />
                  <span>System Health</span>
                </div>
              </button>
              <button
                onClick={() => setActiveTab('team')}
                className={`px-6 py-4 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'team'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Settings className="h-4 w-4" />
                  <span>Team Settings</span>
                </div>
              </button>
              <button
                onClick={() => setActiveTab('users')}
                className={`px-6 py-4 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'users'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Users className="h-4 w-4" />
                  <span>Users & Roles</span>
                </div>
              </button>
            </div>
          </div>

          <div className="p-6">
            {/* System Health Tab */}
            {activeTab === 'system' && (
              <div className="space-y-6">
                {/* Services Health */}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Services Status</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {services.map((service) => (
                      <div
                        key={service.service_name}
                        className="border border-gray-200 rounded-lg p-4"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            {getStatusIcon(service.status)}
                            <div>
                              <h3 className="text-sm font-semibold text-gray-900 capitalize">
                                {service.service_name.replace('_', ' ')}
                              </h3>
                              <p className="text-xs text-gray-600">
                                Uptime: {formatUptime(service.uptime)}
                              </p>
                            </div>
                          </div>
                          <span
                            className={`text-xs px-2 py-0.5 rounded border capitalize ${getStatusColor(
                              service.status
                            )}`}
                          >
                            {service.status}
                          </span>
                        </div>
                        {service.message && (
                          <p className="text-xs text-gray-600 mt-2">{service.message}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Workers */}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Workers</h2>
                  <div className="space-y-3">
                    {workers.map((worker) => (
                      <div
                        key={worker.worker_id}
                        className="border border-gray-200 rounded-lg p-4"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            {getStatusIcon(worker.status)}
                            <div>
                              <h3 className="text-sm font-semibold text-gray-900">
                                {worker.hostname}
                              </h3>
                              <p className="text-xs text-gray-600">
                                {worker.tasks_completed.toLocaleString()} tasks completed
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-4">
                            <span
                              className={`text-xs px-2 py-0.5 rounded border capitalize ${getStatusColor(
                                worker.status
                              )}`}
                            >
                              {worker.status}
                            </span>
                            <div className="text-right text-xs text-gray-600">
                              <div>CPU: {worker.cpu_usage.toFixed(1)}%</div>
                              <div>MEM: {worker.memory_usage.toFixed(1)}%</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Queues */}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Task Queues</h2>
                  <div className="space-y-3">
                    {queues.map((queue) => (
                      <div key={queue.queue_name} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="text-sm font-semibold text-gray-900 capitalize">
                              {queue.queue_name}
                            </h3>
                            <p className="text-xs text-gray-600">
                              Avg wait: {queue.average_wait_time.toFixed(1)}s
                            </p>
                          </div>
                          <div className="flex items-center space-x-6 text-xs">
                            <div className="text-center">
                              <div className="text-yellow-600 font-semibold">
                                {queue.tasks_pending}
                              </div>
                              <div className="text-gray-600">Pending</div>
                            </div>
                            <div className="text-center">
                              <div className="text-blue-600 font-semibold">{queue.tasks_running}</div>
                              <div className="text-gray-600">Running</div>
                            </div>
                            <div className="text-center">
                              <div className="text-green-600 font-semibold">
                                {queue.tasks_completed_24h}
                              </div>
                              <div className="text-gray-600">Completed (24h)</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Storage */}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Storage Systems</h2>
                  <div className="space-y-3">
                    {storage.map((store) => (
                      <div
                        key={store.storage_type}
                        className="border border-gray-200 rounded-lg p-4"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            <HardDrive className="h-5 w-5 text-gray-600" />
                            <div>
                              <h3 className="text-sm font-semibold text-gray-900 uppercase">
                                {store.storage_type}
                              </h3>
                            </div>
                          </div>
                          <span
                            className={`text-xs px-2 py-0.5 rounded border capitalize ${getStatusColor(
                              store.status
                            )}`}
                          >
                            {store.status}
                          </span>
                        </div>
                        {store.total_size && (
                          <div className="mt-2">
                            <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                              <span>
                                {formatBytes(store.used_size)} of {formatBytes(store.total_size)}
                              </span>
                              <span>{store.usage_percentage?.toFixed(1)}%</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full transition-all ${
                                  (store.usage_percentage || 0) > 80
                                    ? 'bg-red-600'
                                    : (store.usage_percentage || 0) > 60
                                      ? 'bg-yellow-600'
                                      : 'bg-green-600'
                                }`}
                                style={{ width: `${store.usage_percentage || 0}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recent Logs */}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Logs</h2>
                  <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                    <div className="space-y-2 font-mono text-xs">
                      {logs.map((log, idx) => (
                        <div key={idx} className="flex items-start space-x-3">
                          <span className="text-gray-500">
                            {format(new Date(log.timestamp), 'HH:mm:ss')}
                          </span>
                          <span
                            className={`font-semibold ${
                              log.level === 'ERROR'
                                ? 'text-red-600'
                                : log.level === 'WARNING'
                                  ? 'text-yellow-600'
                                  : 'text-gray-600'
                            }`}
                          >
                            {log.level}
                          </span>
                          <span className="text-blue-600">[{log.component}]</span>
                          <span className="text-gray-700">{log.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Team Settings Tab */}
            {activeTab === 'team' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Team Information</h2>
                  <div className="border border-gray-200 rounded-lg p-6">
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <label className="text-sm font-medium text-gray-600">Team Name</label>
                        <p className="text-sm text-gray-900 mt-1">Demo Team</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">
                          Subscription Tier
                        </label>
                        <p className="text-sm text-gray-900 mt-1">Professional</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">Team ID</label>
                        <p className="text-sm text-gray-900 mt-1 font-mono">team_001</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">Created</label>
                        <p className="text-sm text-gray-900 mt-1">January 1, 2025</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Integrations</h2>
                  <div className="space-y-3">
                    {[
                      { name: 'OpenAI API', status: 'connected', icon: '🤖' },
                      { name: 'Twilio SMS', status: 'connected', icon: '📱' },
                      { name: 'SendGrid Email', status: 'connected', icon: '📧' },
                      { name: 'Zillow API', status: 'not_configured', icon: '🏠' },
                      { name: 'PropStream', status: 'not_configured', icon: '📊' },
                    ].map((integration) => (
                      <div
                        key={integration.name}
                        className="border border-gray-200 rounded-lg p-4 flex items-center justify-between"
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-2xl">{integration.icon}</span>
                          <div>
                            <h3 className="text-sm font-semibold text-gray-900">
                              {integration.name}
                            </h3>
                          </div>
                        </div>
                        <span
                          className={`text-xs px-2 py-0.5 rounded border capitalize ${
                            integration.status === 'connected'
                              ? 'bg-green-100 text-green-700 border-green-200'
                              : 'bg-gray-100 text-gray-700 border-gray-200'
                          }`}
                        >
                          {integration.status.replace('_', ' ')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Users Tab */}
            {activeTab === 'users' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Team Members</h2>
                  <div className="space-y-3">
                    {[
                      {
                        name: user?.full_name || 'Demo User',
                        email: user?.email || 'demo@example.com',
                        role: user?.role || 'admin',
                        status: 'active',
                      },
                      {
                        name: 'Sarah Johnson',
                        email: 'sarah@example.com',
                        role: 'manager',
                        status: 'active',
                      },
                      {
                        name: 'Mike Chen',
                        email: 'mike@example.com',
                        role: 'agent',
                        status: 'active',
                      },
                    ].map((member) => (
                      <div key={member.email} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                              <span className="text-primary-600 font-semibold">
                                {member.name.charAt(0)}
                              </span>
                            </div>
                            <div>
                              <h3 className="text-sm font-semibold text-gray-900">{member.name}</h3>
                              <p className="text-xs text-gray-600">{member.email}</p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded capitalize">
                              {member.role}
                            </span>
                            <span
                              className={`text-xs px-2 py-0.5 rounded border capitalize ${getStatusColor(
                                member.status
                              )}`}
                            >
                              {member.status}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Role Permissions</h2>
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Permission
                          </th>
                          <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                            Admin
                          </th>
                          <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                            Manager
                          </th>
                          <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                            Agent
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {[
                          { name: 'View Properties', admin: true, manager: true, agent: true },
                          { name: 'Edit Properties', admin: true, manager: true, agent: true },
                          { name: 'Delete Properties', admin: true, manager: true, agent: false },
                          { name: 'Send Communications', admin: true, manager: true, agent: true },
                          { name: 'Manage Templates', admin: true, manager: true, agent: false },
                          { name: 'View Analytics', admin: true, manager: true, agent: true },
                          { name: 'Manage Users', admin: true, manager: false, agent: false },
                          { name: 'System Settings', admin: true, manager: false, agent: false },
                        ].map((perm) => (
                          <tr key={perm.name}>
                            <td className="px-6 py-4 text-sm text-gray-900">{perm.name}</td>
                            <td className="px-6 py-4 text-center">
                              {perm.admin && <CheckCircle className="h-5 w-5 text-green-600 mx-auto" />}
                            </td>
                            <td className="px-6 py-4 text-center">
                              {perm.manager && <CheckCircle className="h-5 w-5 text-green-600 mx-auto" />}
                            </td>
                            <td className="px-6 py-4 text-center">
                              {perm.agent && <CheckCircle className="h-5 w-5 text-green-600 mx-auto" />}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
