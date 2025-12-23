-- ============================================================================
-- Supabase Quota System Schema
-- 
-- This schema provides atomic quota enforcement for OpenAI API usage.
-- It includes the user_quotas table and the consume_quota RPC function.
-- 
-- IMPORTANT: Run this in the Supabase SQL Editor to set up the quota system.
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- User Quotas Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.user_quotas (
    user_id UUID PRIMARY KEY,
    
    -- Daily counters (reset at midnight UTC)
    daily_requests INTEGER NOT NULL DEFAULT 0,
    daily_tokens INTEGER NOT NULL DEFAULT 0,
    last_reset_day DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Monthly counters (reset on 1st of each month)
    monthly_tokens INTEGER NOT NULL DEFAULT 0,
    last_reset_month DATE NOT NULL DEFAULT DATE_TRUNC('month', CURRENT_DATE)::DATE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_quotas_user_id ON public.user_quotas(user_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_user_quotas_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_quotas_updated_at ON public.user_quotas;
CREATE TRIGGER user_quotas_updated_at
    BEFORE UPDATE ON public.user_quotas
    FOR EACH ROW
    EXECUTE FUNCTION update_user_quotas_updated_at();

-- ============================================================================
-- Atomic Quota Consumption Function (consume_quota)
-- 
-- This function performs an atomic check-and-increment operation:
-- 1. Creates user quota record if it doesn't exist
-- 2. Resets daily/monthly counters if needed
-- 3. Checks if user is within limits
-- 4. If allowed, increments the counters and returns success
-- 5. If denied, returns the reason without incrementing
-- ============================================================================

CREATE OR REPLACE FUNCTION public.consume_quota(
    p_user_id UUID,
    p_reserved_tokens INTEGER DEFAULT 2000,
    p_daily_request_limit INTEGER DEFAULT 50,
    p_monthly_token_limit INTEGER DEFAULT 2000000
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER  -- Run with elevated privileges
AS $$
DECLARE
    v_row public.user_quotas%ROWTYPE;
    v_today DATE := CURRENT_DATE;
    v_this_month DATE := DATE_TRUNC('month', CURRENT_DATE)::DATE;
    v_allowed BOOLEAN := TRUE;
    v_reason TEXT := NULL;
BEGIN
    -- Upsert user quota record (create if not exists)
    INSERT INTO public.user_quotas (user_id, daily_requests, daily_tokens, monthly_tokens, last_reset_day, last_reset_month)
    VALUES (p_user_id, 0, 0, 0, v_today, v_this_month)
    ON CONFLICT (user_id) DO NOTHING;
    
    -- Lock the row for update to prevent race conditions
    SELECT * INTO v_row
    FROM public.user_quotas
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Reset daily counters if it's a new day
    IF v_row.last_reset_day < v_today THEN
        v_row.daily_requests := 0;
        v_row.daily_tokens := 0;
        v_row.last_reset_day := v_today;
    END IF;
    
    -- Reset monthly counters if it's a new month
    IF v_row.last_reset_month < v_this_month THEN
        v_row.monthly_tokens := 0;
        v_row.last_reset_month := v_this_month;
    END IF;
    
    -- Check daily request limit
    IF v_row.daily_requests >= p_daily_request_limit THEN
        v_allowed := FALSE;
        v_reason := 'Daily request limit exceeded';
    -- Check monthly token limit
    ELSIF v_row.monthly_tokens + p_reserved_tokens > p_monthly_token_limit THEN
        v_allowed := FALSE;
        v_reason := 'Monthly token limit exceeded';
    END IF;
    
    -- If allowed, increment counters
    IF v_allowed THEN
        UPDATE public.user_quotas
        SET 
            daily_requests = v_row.daily_requests + 1,
            daily_tokens = v_row.daily_tokens + p_reserved_tokens,
            monthly_tokens = v_row.monthly_tokens + p_reserved_tokens,
            last_reset_day = v_row.last_reset_day,
            last_reset_month = v_row.last_reset_month
        WHERE user_id = p_user_id;
        
        -- Return success with updated counters
        RETURN jsonb_build_object(
            'allowed', TRUE,
            'reason', NULL,
            'daily_requests_used', v_row.daily_requests + 1,
            'daily_tokens_used', v_row.daily_tokens + p_reserved_tokens,
            'monthly_tokens_used', v_row.monthly_tokens + p_reserved_tokens,
            'daily_request_limit', p_daily_request_limit,
            'monthly_token_limit', p_monthly_token_limit
        );
    ELSE
        -- Update reset timestamps without incrementing counters
        UPDATE public.user_quotas
        SET 
            last_reset_day = v_row.last_reset_day,
            last_reset_month = v_row.last_reset_month
        WHERE user_id = p_user_id;
        
        -- Return denial with current counters
        RETURN jsonb_build_object(
            'allowed', FALSE,
            'reason', v_reason,
            'daily_requests_used', v_row.daily_requests,
            'daily_tokens_used', v_row.daily_tokens,
            'monthly_tokens_used', v_row.monthly_tokens,
            'daily_request_limit', p_daily_request_limit,
            'monthly_token_limit', p_monthly_token_limit
        );
    END IF;
END;
$$;

-- ============================================================================
-- Quota Status Function (get_quota_status)
-- 
-- Read-only function to get current quota status without consuming quota.
-- Useful for UI display of remaining quota.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_quota_status(
    p_user_id UUID,
    p_daily_request_limit INTEGER DEFAULT 50,
    p_monthly_token_limit INTEGER DEFAULT 2000000
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_row public.user_quotas%ROWTYPE;
    v_today DATE := CURRENT_DATE;
    v_this_month DATE := DATE_TRUNC('month', CURRENT_DATE)::DATE;
BEGIN
    -- Get current quota record
    SELECT * INTO v_row
    FROM public.user_quotas
    WHERE user_id = p_user_id;
    
    -- If no record exists, return zeros
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'daily_requests_used', 0,
            'daily_requests_limit', p_daily_request_limit,
            'daily_requests_remaining', p_daily_request_limit,
            'monthly_tokens_used', 0,
            'monthly_tokens_limit', p_monthly_token_limit,
            'monthly_tokens_remaining', p_monthly_token_limit
        );
    END IF;
    
    -- Calculate effective values (considering resets)
    IF v_row.last_reset_day < v_today THEN
        v_row.daily_requests := 0;
        v_row.daily_tokens := 0;
    END IF;
    
    IF v_row.last_reset_month < v_this_month THEN
        v_row.monthly_tokens := 0;
    END IF;
    
    -- Return current status
    RETURN jsonb_build_object(
        'daily_requests_used', v_row.daily_requests,
        'daily_requests_limit', p_daily_request_limit,
        'daily_requests_remaining', GREATEST(0, p_daily_request_limit - v_row.daily_requests),
        'monthly_tokens_used', v_row.monthly_tokens,
        'monthly_tokens_limit', p_monthly_token_limit,
        'monthly_tokens_remaining', GREATEST(0, p_monthly_token_limit - v_row.monthly_tokens)
    );
END;
$$;

-- ============================================================================
-- Grant Permissions
-- 
-- The consume_quota and get_quota_status functions use SECURITY DEFINER,
-- so they run with the privileges of the function owner (postgres).
-- Grant execute to authenticated users if needed.
-- ============================================================================

-- Grant execute to authenticated role (if using RLS)
-- GRANT EXECUTE ON FUNCTION public.consume_quota TO authenticated;
-- GRANT EXECUTE ON FUNCTION public.get_quota_status TO authenticated;

-- For service role access (recommended for backend):
-- No additional grants needed - service role has full access

-- ============================================================================
-- Verification Query
-- ============================================================================

-- Test the consume_quota function:
-- SELECT public.consume_quota('00000000-0000-0000-0000-000000000001'::uuid);

-- Check quota status:
-- SELECT public.get_quota_status('00000000-0000-0000-0000-000000000001'::uuid);

-- View all user quotas:
-- SELECT * FROM public.user_quotas ORDER BY updated_at DESC;

