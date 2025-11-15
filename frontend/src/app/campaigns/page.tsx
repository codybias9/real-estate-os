'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { campaignsApi } from '@/lib/api';

interface Campaign {
  id: number;
  name: string;
  description: string;
  status: string;
  template_type: string;
  created_at: string;
  updated_at: string;
  scheduled_send_date?: string;
  sent_count: number;
  opened_count: number;
  clicked_count: number;
  replied_count: number;
}

interface CampaignListResponse {
  campaigns: Campaign[];
  total: number;
  page: number;
  page_size: number;
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCampaign, setNewCampaign] = useState({
    name: '',
    description: '',
    template_type: 'investor_outreach',
  });

  useEffect(() => {
    loadCampaigns();
  }, []);

  const loadCampaigns = async () => {
    try {
      const response = await campaignsApi.list();
      setCampaigns(response.data.campaigns || []);
    } catch (error) {
      console.error('Error loading campaigns:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCampaign = async () => {
    try {
      await campaignsApi.create(newCampaign);
      setShowCreateModal(false);
      setNewCampaign({ name: '', description: '', template_type: 'investor_outreach' });
      loadCampaigns();
    } catch (error) {
      console.error('Error creating campaign:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, string> = {
      draft: 'badge-info',
      scheduled: 'badge-warning',
      sending: 'badge-info',
      sent: 'badge-success',
      paused: 'badge-warning',
      completed: 'badge-success',
    };
    return badges[status] || 'badge-info';
  };

  const calculateEngagementRate = (campaign: Campaign) => {
    if (campaign.sent_count === 0) return 0;
    return ((campaign.opened_count / campaign.sent_count) * 100).toFixed(1);
  };

  const calculateClickRate = (campaign: Campaign) => {
    if (campaign.opened_count === 0) return 0;
    return ((campaign.clicked_count / campaign.opened_count) * 100).toFixed(1);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="md:flex md:items-center md:justify-between mb-8">
        <div className="flex-1 min-w-0">
          <h1 className="text-3xl font-bold text-gray-900">Email Campaigns</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage outreach campaigns to property owners and investors
          </p>
        </div>
        <div className="mt-4 flex md:mt-0 md:ml-4">
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            Create Campaign
          </button>
        </div>
      </div>

      {/* Campaign Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="card">
          <p className="text-sm text-gray-600">Total Campaigns</p>
          <p className="text-2xl font-bold text-gray-900">{campaigns.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600">Total Sent</p>
          <p className="text-2xl font-bold text-gray-900">
            {campaigns.reduce((sum, c) => sum + c.sent_count, 0)}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600">Total Opens</p>
          <p className="text-2xl font-bold text-gray-900">
            {campaigns.reduce((sum, c) => sum + c.opened_count, 0)}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600">Total Replies</p>
          <p className="text-2xl font-bold text-gray-900">
            {campaigns.reduce((sum, c) => sum + c.replied_count, 0)}
          </p>
        </div>
      </div>

      {/* Campaigns List */}
      {loading ? (
        <div className="text-center py-12">Loading campaigns...</div>
      ) : campaigns.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500 mb-4">No campaigns yet. Create your first campaign to start outreach.</p>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Create Your First Campaign
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {campaigns.map((campaign) => (
            <div key={campaign.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold text-gray-900">{campaign.name}</h3>
                    <span className={`badge ${getStatusBadge(campaign.status)}`}>
                      {campaign.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{campaign.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span>Type: {campaign.template_type.replace('_', ' ')}</span>
                    <span>Created: {new Date(campaign.created_at).toLocaleDateString()}</span>
                    {campaign.scheduled_send_date && (
                      <span>Scheduled: {new Date(campaign.scheduled_send_date).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Link href={`/campaigns/${campaign.id}`} className="btn-secondary text-sm">
                    View Details
                  </Link>
                  {campaign.status === 'draft' && (
                    <button className="btn-primary text-sm">Launch</button>
                  )}
                </div>
              </div>

              {/* Campaign Metrics */}
              <div className="border-t pt-4">
                <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                  <div>
                    <p className="text-xs text-gray-500">Sent</p>
                    <p className="text-lg font-semibold text-gray-900">{campaign.sent_count}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Opened</p>
                    <p className="text-lg font-semibold text-gray-900">{campaign.opened_count}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Clicked</p>
                    <p className="text-lg font-semibold text-gray-900">{campaign.clicked_count}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Replied</p>
                    <p className="text-lg font-semibold text-gray-900">{campaign.replied_count}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Open Rate</p>
                    <p className="text-lg font-semibold text-green-600">
                      {calculateEngagementRate(campaign)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Click Rate</p>
                    <p className="text-lg font-semibold text-blue-600">
                      {calculateClickRate(campaign)}%
                    </p>
                  </div>
                </div>

                {/* Progress Bar */}
                {campaign.sent_count > 0 && (
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                      <span>Engagement Progress</span>
                      <span>{campaign.opened_count} / {campaign.sent_count} opened</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-500 h-2 rounded-full transition-all"
                        style={{ width: `${calculateEngagementRate(campaign)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Campaign Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Create New Campaign</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Campaign Name
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={newCampaign.name}
                    onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
                    placeholder="e.g., Q4 Investor Outreach"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    className="input"
                    rows={3}
                    value={newCampaign.description}
                    onChange={(e) => setNewCampaign({ ...newCampaign, description: e.target.value })}
                    placeholder="Describe the campaign purpose..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Template Type
                  </label>
                  <select
                    className="input"
                    value={newCampaign.template_type}
                    onChange={(e) => setNewCampaign({ ...newCampaign, template_type: e.target.value })}
                  >
                    <option value="investor_outreach">Investor Outreach</option>
                    <option value="owner_outreach">Owner Outreach</option>
                    <option value="property_alert">Property Alert</option>
                    <option value="market_update">Market Update</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateCampaign}
                  className="btn-primary flex-1"
                  disabled={!newCampaign.name}
                >
                  Create Campaign
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
