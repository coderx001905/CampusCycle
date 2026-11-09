import React, { useEffect, useState, useCallback } from 'react';
import {
  TrendingUp,
  Truck,
  CheckCircle2,
  AlertTriangle,
  Building2,
  Package,
  Layers,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { analyticsApi } from '../api/analytics';

export const AnalyticsView = ({ onNavigate: _onNavigate, onShowToast }) => {
  const { college, isAuthenticated, isPlatformAdmin } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const [summaryData, setSummaryData] = useState(null);
  const [categoryData, setCategoryData] = useState([]);
  const [requestData, setRequestData] = useState(null);
  const [transferData, setTransferData] = useState(null);
  const [collegeData, setCollegeData] = useState(null);

  const fetchAnalytics = useCallback(async (isManualRefresh = false) => {
    if (!isAuthenticated) return;

    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const promises = [
        analyticsApi.getSummary(),
        analyticsApi.getCategories(),
        analyticsApi.getRequests(),
        analyticsApi.getTransfers(),
      ];

      if (isPlatformAdmin) {
        promises.push(
          analyticsApi.getColleges().catch((err) => {
            console.warn('Colleges analytics failed:', err);
            return { data: null };
          })
        );
      }

      const results = await Promise.all(promises);

      const [summaryRes, categoryRes, requestRes, transferRes, collegeRes] = results;

      setSummaryData(summaryRes?.data || null);
      setCategoryData(categoryRes?.data?.items || []);
      setRequestData(requestRes?.data || null);
      setTransferData(transferRes?.data || null);

      if (isPlatformAdmin && collegeRes?.data) {
        setCollegeData(collegeRes.data);
      }

      if (isManualRefresh && onShowToast) {
        onShowToast('Analytics data refreshed', 'success');
      }
    } catch (err) {
      console.error('Failed to load analytics:', err);
      const msg = err?.response?.data?.error?.message || err?.message || 'Failed to load analytics metrics';
      setError(msg);
      if (onShowToast) {
        onShowToast(msg, 'error');
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [isAuthenticated, isPlatformAdmin, onShowToast]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Derived metrics
  const resMetrics = summaryData?.resources || {};
  const reqMetrics = summaryData?.requests || {};
  const transMetrics = summaryData?.transfers || {};
  const colMetrics = summaryData?.colleges || {};

  const totalCategoryQuantity = categoryData.reduce((sum, item) => sum + (item.total_quantity || 0), 0);

  const requestStatusList = requestData?.by_status || [];
  const totalRequests = requestData?.total_requests || 0;
  const fulfillmentRate = requestData?.fulfillment_rate ?? 0;

  const transferStatusList = transferData?.by_status || [];
  const transferDisputes = transferData?.dispute_metrics || {};
  const transferQuantities = transferData?.quantity_metrics || {};

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold tracking-wider text-ui-accent uppercase mb-2">
            <span>WORKSPACE</span>
            <span>/</span>
            <span>ANALYTICS</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
              {isPlatformAdmin ? 'Global Platform Scope' : `${college?.name || 'College Workspace'} (Scoped)`}
            </span>
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            {isPlatformAdmin ? 'Platform-Wide Analytics & Operations' : 'Campus Analytics Overview'}
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            {isPlatformAdmin
              ? 'Real-time database aggregated metrics for college participation, inventory levels, requests, and transfer disputes.'
              : `Real-time database analytics for resources, requests, inventory, and transfer logistics belonging to ${college?.name || 'your institution'}.`}
          </p>
        </div>

        <button
          type="button"
          onClick={() => fetchAnalytics(true)}
          disabled={isLoading || isRefreshing}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-ui-border bg-ui-surface hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-200 transition shadow-sm disabled:opacity-50"
        >
          <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
          {isRefreshing ? 'Refreshing...' : 'Refresh Metrics'}
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/30 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div className="flex-1 text-xs text-red-800 dark:text-red-200">
            <h4 className="font-bold">Failed to load analytics data</h4>
            <p className="mt-0.5">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => fetchAnalytics(false)}
            className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 rounded-2xl border border-ui-border bg-ui-surface animate-pulse p-5" />
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="h-64 rounded-2xl border border-ui-border bg-ui-surface animate-pulse p-6" />
            <div className="h-64 rounded-2xl border border-ui-border bg-ui-surface animate-pulse p-6" />
          </div>
          <div className="h-80 rounded-2xl border border-ui-border bg-ui-surface animate-pulse p-6" />
        </div>
      ) : (
        <>
          {/* Top KPI Cards Row */}
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {isPlatformAdmin ? (
              <>
                <article className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-ui-text-secondary">Tracked Colleges</p>
                    <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                      <Building2 size={19} />
                    </div>
                  </div>
                  <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                    {colMetrics.total_colleges || 0}
                  </p>
                  <p className="mt-2 text-xs text-ui-text-secondary">
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">{colMetrics.verified_colleges || 0} verified</span>
                    {' • '}
                    <span className="text-amber-600 dark:text-amber-400">{colMetrics.pending_colleges || 0} pending</span>
                  </p>
                </article>

                <article className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-ui-text-secondary">Network Listings</p>
                    <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400">
                      <Package size={19} />
                    </div>
                  </div>
                  <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                    {resMetrics.total_listings || 0}
                  </p>
                  <p className="mt-2 text-xs text-ui-text-secondary">
                    {resMetrics.available_quantity || 0} available units across colleges
                  </p>
                </article>

                <article className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-ui-text-secondary">Network Requests</p>
                    <div className="p-2.5 rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400">
                      <TrendingUp size={19} />
                    </div>
                  </div>
                  <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                    {reqMetrics.total_requests || 0}
                  </p>
                  <p className="mt-2 text-xs text-ui-text-secondary">
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">{fulfillmentRate}%</span> fulfillment rate
                  </p>
                </article>

                <article className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-ui-text-secondary">Transfer Operations</p>
                    <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
                      <Truck size={19} />
                    </div>
                  </div>
                  <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                    {transMetrics.total_transfers || 0}
                  </p>
                  <p className="mt-2 text-xs text-ui-text-secondary">
                    {transMetrics.completed_transfers || 0} completed • {transMetrics.disputed_transfers || 0} disputed
                  </p>
                </article>
              </>
            ) : (
              <>
                <article className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-ui-text-secondary">My College Listings</p>
                    <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                      <Package size={19} />
                    </div>
                  </div>
                  <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                    {resMetrics.total_listings || 0}
                  </p>
                  <p className="mt-2 text-xs text-ui-text-secondary">
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">{resMetrics.active_listings || 0} active</span>
                    {' • '}
                    <span>{resMetrics.available_quantity || 0} units in stock</span>
                  </p>
                </article>

                <article className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-ui-text-secondary">Requests Handled</p>
                    <div className="p-2.5 rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400">
                      <TrendingUp size={19} />
                    </div>
                  </div>
                  <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                    {reqMetrics.total_requests || 0}
                  </p>
                  <p className="mt-2 text-xs text-ui-text-secondary">
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">{fulfillmentRate}%</span> fulfillment rate
                  </p>
                </article>

                <article className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-ui-text-secondary">Active Shipments</p>
                    <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400">
                      <Truck size={19} />
                    </div>
                  </div>
                  <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                    {(transMetrics.preparing_transfers || 0) + (transMetrics.dispatched_transfers || 0) + (transMetrics.partially_received_transfers || 0)}
                  </p>
                  <p className="mt-2 text-xs text-ui-text-secondary">
                    {transMetrics.dispatched_transfers || 0} currently in transit
                  </p>
                </article>

                <article className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-ui-text-secondary">Completed Transfers</p>
                    <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
                      <CheckCircle2 size={19} />
                    </div>
                  </div>
                  <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                    {transMetrics.completed_transfers || 0}
                  </p>
                  <p className="mt-2 text-xs text-ui-text-secondary">
                    Successfully verified and delivered
                  </p>
                </article>
              </>
            )}
          </section>

          {/* Performance & Logistics Details */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Request Performance Card */}
            <div className="rounded-2xl border border-ui-border bg-ui-surface p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-display text-base font-bold text-slate-900 dark:text-white">Request Performance</h2>
                  <p className="mt-1 text-xs text-ui-text-secondary">Request distribution, fulfillment & workflow status</p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{fulfillmentRate}%</p>
                  <p className="text-[10px] text-ui-text-secondary uppercase font-semibold">Fulfillment</p>
                </div>
              </div>

              {/* Progress bar for fulfillment */}
              <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, fulfillmentRate))}%` }}
                />
              </div>

              {/* Status List */}
              <div className="mt-6 space-y-3">
                <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Statuses</h3>
                {requestStatusList.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No requests recorded yet.</p>
                ) : (
                  requestStatusList.map((item) => {
                    const pct = totalRequests > 0 ? Math.round((item.count / totalRequests) * 100) : 0;
                    const statusColors = {
                      pending: 'bg-amber-500',
                      approved: 'bg-blue-500',
                      in_progress: 'bg-indigo-500',
                      completed: 'bg-emerald-500',
                      rejected: 'bg-red-500',
                      cancelled: 'bg-slate-500',
                    };
                    const color = statusColors[item.status] || 'bg-slate-400';

                    return (
                      <div key={item.status}>
                        <div className="mb-1 flex justify-between text-xs">
                          <span className="font-medium capitalize text-slate-700 dark:text-slate-200">
                            {item.status.replace('_', ' ')}
                          </span>
                          <span className="text-ui-text-secondary">
                            {item.count} ({pct}%)
                          </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                          <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Request Type breakdown */}
              {requestData?.by_type && requestData.by_type.length > 0 && (
                <div className="mt-6 pt-5 border-t border-ui-border">
                  <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                    Distribution by Type
                  </h3>
                  <div className="grid grid-cols-3 gap-2">
                    {requestData.by_type.map((t) => (
                      <div key={t.request_type} className="p-2.5 rounded-xl border border-ui-border bg-slate-50/50 dark:bg-slate-900/50 text-center">
                        <p className="text-xs font-medium text-slate-500 capitalize">{t.request_type}</p>
                        <p className="mt-1 text-base font-bold text-slate-900 dark:text-white">{t.count}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Transfer Logistics & Physical Deliveries Card */}
            <div className="rounded-2xl border border-ui-border bg-ui-surface p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-display text-base font-bold text-slate-900 dark:text-white">Logistics & Physical Receipts</h2>
                  <p className="mt-1 text-xs text-ui-text-secondary">Shipment status, dispute tracking & inventory received</p>
                </div>
                <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400">
                  <Truck size={18} />
                </div>
              </div>

              {/* Physical Quantities Meter */}
              <div className="mt-4 grid grid-cols-4 gap-2">
                <div className="p-2.5 rounded-xl border border-ui-border bg-slate-50/50 dark:bg-slate-900/50 text-center">
                  <p className="text-[11px] font-semibold text-slate-500">Shipped</p>
                  <p className="mt-1 text-base font-bold text-slate-900 dark:text-white">{transferQuantities.total_shipped || 0}</p>
                </div>
                <div className="p-2.5 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-center">
                  <p className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">Good</p>
                  <p className="mt-1 text-base font-bold text-emerald-600 dark:text-emerald-400">{transferQuantities.received_good || 0}</p>
                </div>
                <div className="p-2.5 rounded-xl border border-amber-500/20 bg-amber-500/5 text-center">
                  <p className="text-[11px] font-semibold text-amber-600 dark:text-amber-400">Damaged</p>
                  <p className="mt-1 text-base font-bold text-amber-600 dark:text-amber-400">{transferQuantities.damaged || 0}</p>
                </div>
                <div className="p-2.5 rounded-xl border border-red-500/20 bg-red-500/5 text-center">
                  <p className="text-[11px] font-semibold text-red-600 dark:text-red-400">Missing</p>
                  <p className="mt-1 text-base font-bold text-red-600 dark:text-red-400">{transferQuantities.missing || 0}</p>
                </div>
              </div>

              {/* Status List */}
              <div className="mt-6 space-y-3">
                <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Transfer Stages</h3>
                {transferStatusList.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No transfers initiated yet.</p>
                ) : (
                  transferStatusList.map((item) => {
                    const totalT = transMetrics.total_transfers || 1;
                    const pct = Math.round((item.count / totalT) * 100);
                    return (
                      <div key={item.status}>
                        <div className="mb-1 flex justify-between text-xs">
                          <span className="font-medium capitalize text-slate-700 dark:text-slate-200">
                            {item.status.replace('_', ' ')}
                          </span>
                          <span className="text-ui-text-secondary">
                            {item.count} batch{item.count !== 1 ? 'es' : ''} ({pct}%)
                          </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                          <div className="h-full rounded-full bg-indigo-500" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Dispute Tracking Banner */}
              <div className="mt-6 pt-5 border-t border-ui-border flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={16} className={transferDisputes.open_disputes > 0 ? 'text-amber-500' : 'text-slate-400'} />
                  <span className="font-medium text-slate-700 dark:text-slate-200">Dispute Resolutions</span>
                </div>
                <div className="flex gap-3">
                  <span>Total: <strong>{transferDisputes.total_disputed || 0}</strong></span>
                  <span className="text-emerald-600 dark:text-emerald-400">Resolved: <strong>{transferDisputes.resolved_disputes || 0}</strong></span>
                  <span className="text-amber-600 dark:text-amber-400">Pending: <strong>{transferDisputes.open_disputes || 0}</strong></span>
                </div>
              </div>
            </div>
          </div>

          {/* Resource Category Distribution */}
          <div className="rounded-2xl border border-ui-border bg-ui-surface p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-display text-base font-bold text-slate-900 dark:text-white">Resource Category Distribution</h2>
                <p className="mt-1 text-xs text-ui-text-secondary">
                  Real database breakdown across registered categories and available physical quantities
                </p>
              </div>
              <div className="p-2 rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                <Layers size={18} />
              </div>
            </div>

            <div className="mt-6 space-y-4">
              {categoryData.length === 0 ? (
                <p className="text-xs text-slate-400 italic py-4 text-center">No categories with active listings found.</p>
              ) : (
                categoryData.map((category) => {
                  const percentage = totalCategoryQuantity > 0 ? Math.round((category.total_quantity / totalCategoryQuantity) * 100) : 0;

                  return (
                    <div key={category.category} className="space-y-1.5">
                      <div className="flex justify-between items-center text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-800 dark:text-slate-100">{category.category}</span>
                          <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                            {category.total_listings} listing{category.total_listings !== 1 ? 's' : ''}
                          </span>
                        </div>
                        <div className="text-right text-xs">
                          <span className="font-medium text-slate-900 dark:text-white">{category.total_quantity} units</span>
                          <span className="text-ui-text-secondary ml-1.5">({category.available_quantity} avail • {category.reserved_quantity} rsvd)</span>
                        </div>
                      </div>

                      <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                        <div className="h-full rounded-full bg-blue-600 dark:bg-blue-500 transition-all duration-300" style={{ width: `${percentage}%` }} />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Platform Admin Exclusive: Participating Colleges Leaderboard */}
          {isPlatformAdmin && collegeData && (
            <div className="rounded-2xl border border-ui-border bg-ui-surface p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-display text-base font-bold text-slate-900 dark:text-white">Institution Participation & Activity</h2>
                  <p className="mt-1 text-xs text-ui-text-secondary">
                    Active listings, verification states, and completed inter-college transfers
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs font-semibold text-ui-accent">
                  <Building2 size={16} />
                  <span>{collegeData.total_colleges || 0} Registered</span>
                </div>
              </div>

              <div className="mt-6 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-ui-border text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">
                      <th className="pb-3 pl-2">Institution</th>
                      <th className="pb-3">Verification</th>
                      <th className="pb-3 text-center">Active Listings</th>
                      <th className="pb-3 text-center">Completed Transfers</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ui-border">
                    {collegeData.top_participating_colleges?.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="py-4 text-center text-slate-400 italic">No colleges registered.</td>
                      </tr>
                    ) : (
                      collegeData.top_participating_colleges?.map((col) => (
                        <tr key={col.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition">
                          <td className="py-3 pl-2 font-medium text-slate-900 dark:text-white">
                            {col.name}
                          </td>
                          <td className="py-3">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                col.verification_status === 'verified'
                                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                  : col.verification_status === 'pending'
                                  ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                                  : 'bg-red-500/10 text-red-600 dark:text-red-400'
                              }`}
                            >
                              {col.verification_status}
                            </span>
                          </td>
                          <td className="py-3 text-center font-semibold text-slate-700 dark:text-slate-300">
                            {col.active_listings_count}
                          </td>
                          <td className="py-3 text-center font-semibold text-emerald-600 dark:text-emerald-400">
                            {col.completed_transfers_count}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AnalyticsView;
