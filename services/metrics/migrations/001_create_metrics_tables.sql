-- Migration: Create metrics tables for portfolio aggregation
-- Author: Real Estate OS Team
-- Date: 2025-11-03

-- ============================================================
-- Table: metrics_daily
-- Purpose: Daily aggregated metrics per tenant for historical analysis
-- ============================================================

CREATE TABLE IF NOT EXISTS metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    day DATE NOT NULL,

    -- Stage counts (snapshot at end of day)
    stage_new INTEGER DEFAULT 0,
    stage_qualified INTEGER DEFAULT 0,
    stage_enriched INTEGER DEFAULT 0,
    stage_pitched INTEGER DEFAULT 0,
    stage_negotiating INTEGER DEFAULT 0,
    stage_closed_won INTEGER DEFAULT 0,
    stage_closed_lost INTEGER DEFAULT 0,
    stage_archived INTEGER DEFAULT 0,

    -- Conversion rates (%)
    conversion_new_to_qualified DECIMAL(5,2),
    conversion_qualified_to_enriched DECIMAL(5,2),
    conversion_enriched_to_pitched DECIMAL(5,2),
    conversion_pitched_to_won DECIMAL(5,2),
    conversion_overall DECIMAL(5,2),

    -- Response rates (outreach)
    outreach_sends INTEGER DEFAULT 0,
    outreach_delivered INTEGER DEFAULT 0,
    outreach_opens INTEGER DEFAULT 0,
    outreach_clicks INTEGER DEFAULT 0,
    outreach_replies INTEGER DEFAULT 0,
    response_rate_delivered DECIMAL(5,2),
    response_rate_opened DECIMAL(5,2),
    response_rate_replied DECIMAL(5,2),

    -- Time to stage (median hours)
    time_to_qualified_hrs DECIMAL(10,2),
    time_to_enriched_hrs DECIMAL(10,2),
    time_to_pitched_hrs DECIMAL(10,2),
    time_to_closed_hrs DECIMAL(10,2),

    -- Memos generated
    memos_generated INTEGER DEFAULT 0,
    memos_avg_duration_sec DECIMAL(10,2),
    memos_p95_duration_sec DECIMAL(10,2),

    -- Cost tracking
    total_cost_usd DECIMAL(10,2) DEFAULT 0.00,
    avg_cost_per_property DECIMAL(10,2),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, day)
);

-- Indexes for metrics_daily
CREATE INDEX idx_metrics_daily_tenant_day ON metrics_daily(tenant_id, day DESC);
CREATE INDEX idx_metrics_daily_tenant_created ON metrics_daily(tenant_id, created_at DESC);

-- RLS for metrics_daily
ALTER TABLE metrics_daily ENABLE ROW LEVEL SECURITY;

CREATE POLICY metrics_daily_tenant_isolation ON metrics_daily
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- ============================================================
-- Table: metrics_realtime
-- Purpose: Rolling 24h metrics for real-time dashboard
-- ============================================================

CREATE TABLE IF NOT EXISTS metrics_realtime (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    window_hrs INTEGER NOT NULL DEFAULT 24, -- Rolling window size

    -- Counters (JSON for flexibility)
    counters JSONB DEFAULT '{}'::JSONB,

    -- Quick access fields (denormalized from counters)
    total_leads INTEGER DEFAULT 0,
    qualified_count INTEGER DEFAULT 0,
    memos_generated INTEGER DEFAULT 0,
    outreach_sends INTEGER DEFAULT 0,
    outreach_opens INTEGER DEFAULT 0,
    outreach_replies INTEGER DEFAULT 0,

    -- Calculated rates
    qualified_rate DECIMAL(5,2),
    memo_conversion_rate DECIMAL(5,2),
    open_rate DECIMAL(5,2),
    reply_rate DECIMAL(5,2),

    -- Metadata
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, window_hrs, window_start)
);

-- Indexes for metrics_realtime
CREATE INDEX idx_metrics_realtime_tenant_window ON metrics_realtime(tenant_id, window_start DESC);
CREATE INDEX idx_metrics_realtime_calculated ON metrics_realtime(calculated_at DESC);

-- RLS for metrics_realtime
ALTER TABLE metrics_realtime ENABLE ROW LEVEL SECURITY;

CREATE POLICY metrics_realtime_tenant_isolation ON metrics_realtime
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- ============================================================
-- Table: metrics_template_performance
-- Purpose: Per-template outreach performance for optimization
-- ============================================================

CREATE TABLE IF NOT EXISTS metrics_template_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    template_id VARCHAR(100) NOT NULL,
    template_name VARCHAR(255),
    channel VARCHAR(50), -- email, sms, postal

    -- Daily stats
    day DATE NOT NULL,
    sends INTEGER DEFAULT 0,
    delivered INTEGER DEFAULT 0,
    opens INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    bounces INTEGER DEFAULT 0,
    unsubscribes INTEGER DEFAULT 0,

    -- Calculated rates
    delivery_rate DECIMAL(5,2),
    open_rate DECIMAL(5,2),
    click_rate DECIMAL(5,2),
    reply_rate DECIMAL(5,2),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, template_id, day)
);

-- Indexes for metrics_template_performance
CREATE INDEX idx_metrics_template_tenant_day ON metrics_template_performance(tenant_id, day DESC);
CREATE INDEX idx_metrics_template_reply_rate ON metrics_template_performance(tenant_id, reply_rate DESC NULLS LAST);

-- RLS for metrics_template_performance
ALTER TABLE metrics_template_performance ENABLE ROW LEVEL SECURITY;

CREATE POLICY metrics_template_tenant_isolation ON metrics_template_performance
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- ============================================================
-- Functions: Update timestamps
-- ============================================================

CREATE OR REPLACE FUNCTION update_metrics_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER metrics_daily_updated_at
    BEFORE UPDATE ON metrics_daily
    FOR EACH ROW
    EXECUTE FUNCTION update_metrics_updated_at();

CREATE TRIGGER metrics_template_updated_at
    BEFORE UPDATE ON metrics_template_performance
    FOR EACH ROW
    EXECUTE FUNCTION update_metrics_updated_at();

-- ============================================================
-- Grant permissions
-- ============================================================

GRANT SELECT, INSERT, UPDATE ON metrics_daily TO realestate_app;
GRANT SELECT, INSERT, UPDATE ON metrics_realtime TO realestate_app;
GRANT SELECT, INSERT, UPDATE ON metrics_template_performance TO realestate_app;

-- ============================================================
-- Comments
-- ============================================================

COMMENT ON TABLE metrics_daily IS 'Daily aggregated portfolio metrics per tenant';
COMMENT ON TABLE metrics_realtime IS 'Rolling 24-hour metrics for real-time dashboard';
COMMENT ON TABLE metrics_template_performance IS 'Per-template outreach performance tracking';
