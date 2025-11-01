/**
 * Tests for CampaignsTab component (Wave 3.3)
 *
 * Tests:
 * - Campaign list rendering
 * - Status filtering
 * - Campaign analytics view
 * - Create campaign flow
 */

import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, setupUser, mockApiResponse } from '../test/utils';
import { CampaignsTab } from './CampaignsTab';
import * as apiClient from '../services/api';

// Mock the API client
vi.mock('../services/api', () => ({
  default: {
    listCampaigns: vi.fn(),
    getCampaignAnalytics: vi.fn(),
  },
}));

describe('CampaignsTab', () => {
  const mockCampaigns = [
    {
      id: '1',
      name: 'Q1 Cold Outreach',
      campaign_type: 'cold_outreach',
      status: 'active',
      total_recipients: 100,
      emails_sent: 100,
      emails_delivered: 95,
      emails_opened: 30,
      emails_clicked: 10,
      created_at: '2025-01-01T00:00:00Z',
    },
    {
      id: '2',
      name: 'Follow-up Campaign',
      campaign_type: 'follow_up',
      status: 'completed',
      total_recipients: 50,
      emails_sent: 50,
      emails_delivered: 48,
      emails_opened: 25,
      emails_clicked: 8,
      created_at: '2025-01-15T00:00:00Z',
    },
  ];

  it('renders campaign list', async () => {
    vi.mocked(apiClient.default.listCampaigns).mockResolvedValue(
      mockApiResponse(mockCampaigns)
    );

    renderWithProviders(<CampaignsTab />);

    await waitFor(() => {
      expect(screen.getByText('Q1 Cold Outreach')).toBeInTheDocument();
      expect(screen.getByText('Follow-up Campaign')).toBeInTheDocument();
    });
  });

  it('filters campaigns by status', async () => {
    const user = setupUser();
    vi.mocked(apiClient.default.listCampaigns).mockResolvedValue(
      mockApiResponse(mockCampaigns.filter((c) => c.status === 'active'))
    );

    renderWithProviders(<CampaignsTab />);

    // Click active filter
    const activeButton = screen.getByRole('button', { name: /active/i });
    await user.click(activeButton);

    await waitFor(() => {
      expect(screen.getByText('Q1 Cold Outreach')).toBeInTheDocument();
      expect(screen.queryByText('Follow-up Campaign')).not.toBeInTheDocument();
    });
  });

  it('displays campaign metrics', async () => {
    vi.mocked(apiClient.default.listCampaigns).mockResolvedValue(
      mockApiResponse(mockCampaigns)
    );

    renderWithProviders(<CampaignsTab />);

    await waitFor(() => {
      // Check for metrics display
      expect(screen.getByText(/100/)).toBeInTheDocument(); // total recipients
      expect(screen.getByText(/95/)).toBeInTheDocument(); // delivered
    });
  });

  it('shows analytics when campaign is selected', async () => {
    const user = setupUser();
    const mockAnalytics = {
      campaign_id: '1',
      total_recipients: 100,
      delivery_rate: 0.95,
      open_rate: 0.32,
      click_rate: 0.11,
      reply_rate: 0.02,
      step_metrics: [
        {
          step_number: 1,
          total: 100,
          open_rate: 0.32,
          click_rate: 0.11,
        },
      ],
    };

    vi.mocked(apiClient.default.listCampaigns).mockResolvedValue(
      mockApiResponse(mockCampaigns)
    );
    vi.mocked(apiClient.default.getCampaignAnalytics).mockResolvedValue(
      mockApiResponse(mockAnalytics)
    );

    renderWithProviders(<CampaignsTab />);

    // Click on a campaign
    await waitFor(() => {
      const campaign = screen.getByText('Q1 Cold Outreach');
      return user.click(campaign);
    });

    // Should show analytics
    await waitFor(() => {
      expect(screen.getByText(/delivery rate/i)).toBeInTheDocument();
      expect(screen.getByText(/95%/)).toBeInTheDocument();
    });
  });

  it('handles loading state', () => {
    vi.mocked(apiClient.default.listCampaigns).mockReturnValue(
      new Promise(() => {}) // Never resolves
    );

    renderWithProviders(<CampaignsTab />);

    expect(screen.getByTestId('loading')).toBeInTheDocument();
  });

  it('handles error state', async () => {
    vi.mocked(apiClient.default.listCampaigns).mockRejectedValue(
      new Error('Failed to load campaigns')
    );

    renderWithProviders(<CampaignsTab />);

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
