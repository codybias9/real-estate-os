/**
 * CampaignsTab - Email Campaign Management
 *
 * Wave 3.3 - Simple campaign list and analytics viewer
 * Full campaign builder UI can be added in future iteration
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Mail,
  Play,
  Pause,
  BarChart3,
  Users,
  TrendingUp,
  MousePointerClick,
  Reply,
  UserMinus,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { apiClient } from '@/services/api';
import type { Campaign, CampaignAnalytics } from '@/types/provenance';

export function CampaignsTab() {
  const [selectedStatus, setSelectedStatus] = useState<string | undefined>(undefined);
  const [selectedCampaign, setSelectedCampaign] = useState<string | null>(null);

  // Fetch campaigns
  const {
    data: campaigns,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['campaigns', selectedStatus],
    queryFn: () => apiClient.listCampaigns(selectedStatus, 50),
    staleTime: 60 * 1000, // 1 minute
  });

  // Fetch analytics for selected campaign
  const {
    data: analytics,
    isLoading: analyticsLoading,
  } = useQuery({
    queryKey: ['campaign-analytics', selectedCampaign],
    queryFn: () => apiClient.getCampaignAnalytics(selectedCampaign!),
    enabled: !!selectedCampaign,
    staleTime: 30 * 1000, // 30 seconds
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <Mail className="mx-auto h-12 w-12 animate-pulse text-primary-500" />
          <p className="mt-4 text-sm text-gray-500">Loading campaigns...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-start">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Failed to Load Campaigns</h3>
              <p className="mt-1 text-sm text-red-700">
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Email Campaigns</h2>
          <p className="mt-1 text-sm text-gray-500">
            Manage multi-step outreach campaigns
          </p>
        </div>
      </div>

      {/* Status Filter */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setSelectedStatus(undefined)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedStatus === undefined
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All
        </button>
        {['draft', 'active', 'paused', 'completed'].map((status) => (
          <button
            key={status}
            onClick={() => setSelectedStatus(status)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedStatus === status
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Campaign List or Analytics */}
      {selectedCampaign && analytics ? (
        <CampaignAnalyticsView
          campaign={campaigns?.find((c) => c.id === selectedCampaign)!}
          analytics={analytics}
          onBack={() => setSelectedCampaign(null)}
        />
      ) : (
        <CampaignList
          campaigns={campaigns || []}
          onSelectCampaign={setSelectedCampaign}
        />
      )}
    </div>
  );
}

function CampaignList({
  campaigns,
  onSelectCampaign,
}: {
  campaigns: Campaign[];
  onSelectCampaign: (id: string) => void;
}) {
  if (campaigns.length === 0) {
    return (
      <div className="text-center py-12">
        <Mail className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-sm font-medium text-gray-900">No campaigns found</h3>
        <p className="mt-2 text-sm text-gray-500">
          Get started by creating your first email campaign
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {campaigns.map((campaign) => (
        <CampaignCard
          key={campaign.id}
          campaign={campaign}
          onClick={() => onSelectCampaign(campaign.id)}
        />
      ))}
    </div>
  );
}

function CampaignCard({
  campaign,
  onClick,
}: {
  campaign: Campaign;
  onClick: () => void;
}) {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'active':
        return {
          icon: Play,
          color: 'text-green-600',
          bg: 'bg-green-100',
          label: 'Active',
        };
      case 'paused':
        return {
          icon: Pause,
          color: 'text-yellow-600',
          bg: 'bg-yellow-100',
          label: 'Paused',
        };
      case 'completed':
        return {
          icon: CheckCircle2,
          color: 'text-blue-600',
          bg: 'bg-blue-100',
          label: 'Completed',
        };
      default:
        return {
          icon: Mail,
          color: 'text-gray-600',
          bg: 'bg-gray-100',
          label: 'Draft',
        };
    }
  };

  const statusConfig = getStatusConfig(campaign.status);
  const StatusIcon = statusConfig.icon;

  const openRate = campaign.emails_delivered > 0
    ? (campaign.emails_opened / campaign.emails_delivered) * 100
    : 0;

  return (
    <div
      onClick={onClick}
      className="rounded-lg border border-gray-200 bg-white p-6 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900">{campaign.name}</h3>
            <span
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}
            >
              <StatusIcon className="h-3 w-3" />
              {statusConfig.label}
            </span>
          </div>

          {campaign.description && (
            <p className="mt-2 text-sm text-gray-600">{campaign.description}</p>
          )}

          <div className="mt-4 flex items-center gap-6 text-sm text-gray-500">
            <div className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              <span>{campaign.total_recipients} recipients</span>
            </div>
            <div className="flex items-center gap-1">
              <Mail className="h-4 w-4" />
              <span>{campaign.emails_sent} sent</span>
            </div>
            <div className="flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              <span>{openRate.toFixed(1)}% open rate</span>
            </div>
          </div>
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
          className="ml-4 px-4 py-2 text-sm font-medium text-primary-600 hover:text-primary-700"
        >
          View Analytics →
        </button>
      </div>
    </div>
  );
}

function CampaignAnalyticsView({
  campaign,
  analytics,
  onBack,
}: {
  campaign: Campaign;
  analytics: CampaignAnalytics;
  onBack: () => void;
}) {
  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="text-sm text-primary-600 hover:text-primary-700 font-medium"
      >
        ← Back to campaigns
      </button>

      {/* Campaign Header */}
      <div>
        <h3 className="text-xl font-semibold text-gray-900">{campaign.name}</h3>
        {campaign.description && (
          <p className="mt-1 text-sm text-gray-600">{campaign.description}</p>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Delivery Rate"
          value={`${(analytics.delivery_rate * 100).toFixed(1)}%`}
          icon={Mail}
          color="blue"
        />
        <MetricCard
          label="Open Rate"
          value={`${(analytics.open_rate * 100).toFixed(1)}%`}
          icon={TrendingUp}
          color="green"
        />
        <MetricCard
          label="Click Rate"
          value={`${(analytics.click_rate * 100).toFixed(1)}%`}
          icon={MousePointerClick}
          color="purple"
        />
        <MetricCard
          label="Reply Rate"
          value={`${(analytics.reply_rate * 100).toFixed(1)}%`}
          icon={Reply}
          color="indigo"
        />
      </div>

      {/* Detailed Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Recipients" value={analytics.total_recipients} />
        <StatCard label="Sent" value={analytics.sent} />
        <StatCard label="Delivered" value={analytics.delivered} />
        <StatCard label="Opened" value={analytics.opened} />
        <StatCard label="Clicked" value={analytics.clicked} />
        <StatCard label="Replied" value={analytics.replied} />
        <StatCard label="Unsubscribed" value={analytics.unsubscribed} color="red" />
        <StatCard label="Bounced" value={analytics.bounced} color="orange" />
      </div>

      {/* Step Performance */}
      {analytics.step_metrics && analytics.step_metrics.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Step Performance</h4>
          <div className="space-y-4">
            {analytics.step_metrics.map((step) => (
              <div key={step.step_number} className="flex items-center gap-4">
                <div className="w-20 text-sm font-medium text-gray-700">
                  Step {step.step_number}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-gray-600">{step.total} sent</span>
                    <span className="text-gray-900 font-medium">
                      {(step.open_rate * 100).toFixed(1)}% open rate
                    </span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-600 transition-all"
                      style={{ width: `${step.open_rate * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  icon: any;
  color: string;
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    indigo: 'bg-indigo-50 text-indigo-600',
  }[color] || 'bg-gray-50 text-gray-600';

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className={`inline-flex items-center justify-center w-10 h-10 rounded-lg ${colorClasses} mb-3`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="text-2xl font-semibold text-gray-900">{value}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  const textColor = color === 'red' ? 'text-red-600' : color === 'orange' ? 'text-orange-600' : 'text-gray-900';

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className={`text-2xl font-semibold ${textColor}`}>{value.toLocaleString()}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </div>
  );
}
