import React, { useEffect, useState } from 'react';
import {
  ShoppingBag,
  BookOpen,
  Truck,
  Plus,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Loader2,
  AlertCircle,
  Building2,
  Computer,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { resourcesApi } from '../api/resources';
import { requestsApi } from '../api/requests';
import { transfersApi } from '../api/transfers';
import { analyticsApi } from '../api/analytics';

export const DashboardView = ({ onNavigate, onOpenLogin, onOpenRegister }) => {
  const { user, college, isAuthenticated, isPlatformAdmin, isCollegeRep } = useAuth();
  const [stats, setStats] = useState({
    activeListings: 0,
    pendingRequests: 0,
    activeTransfers: 0,
    inventoryAvailable: 0,
    trackedColleges: 0,
  });
  const [recentRequests, setRecentRequests] = useState([]);
  const [recentTransfers, setRecentTransfers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;

    let mounted = true;
    setIsLoading(true);

    const loadDashboardData = async () => {
      try {
        const promises = [
          analyticsApi.getSummary().catch((err) => {
            console.warn('Analytics summary unavailable, falling back to resource list:', err);
            return null;
          }),
        ];

        if (isCollegeRep) {
          promises.push(
            requestsApi.getReceived(1, 4).catch(() => ({ data: { items: [], total: 0 } })),
            transfersApi.listTransfers({ page_size: 4 }).catch(() => ({ data: { items: [], total: 0 } }))
          );
        } else if (isPlatformAdmin) {
          promises.push(
            Promise.resolve({ data: { items: [], total: 0 } }),
            transfersApi.listTransfers({ page_size: 4 }).catch(() => ({ data: { items: [], total: 0 } }))
          );
        }

        const [summaryRes, recReq, transList] = await Promise.all(promises);

        if (!mounted) return;

        if (summaryRes?.data) {
          const summary = summaryRes.data;
          const resMetrics = summary.resources || {};
          const reqMetrics = summary.requests || {};
          const transMetrics = summary.transfers || {};
          const colMetrics = summary.colleges || {};

          const activeTransfersCount =
            (transMetrics.preparing_transfers || 0) +
            (transMetrics.dispatched_transfers || 0) +
            (transMetrics.partially_received_transfers || 0);

          setStats({
            activeListings: resMetrics.active_listings ?? resMetrics.total_listings ?? 0,
            pendingRequests: reqMetrics.pending_requests ?? 0,
            activeTransfers: activeTransfersCount,
            inventoryAvailable: resMetrics.available_quantity ?? 0,
            trackedColleges: colMetrics.total_colleges ?? 0,
          });
        } else {
          // Fallback if summary endpoint failed
          const resList = await resourcesApi.listResources({ page_size: 1 }).catch(() => null);
          const transfers = transList?.data?.items || [];
          const activeTransfersCount = transfers.filter(
            (t) => t.status === 'in_transit' || t.status === 'pending_dispatch' || t.status === 'disputed'
          ).length;

          setStats({
            activeListings: resList?.data?.total || 0,
            pendingRequests: recReq?.data?.items?.filter((r) => r.status === 'pending').length || 0,
            activeTransfers: activeTransfersCount,
            inventoryAvailable: 0,
            trackedColleges: 0,
          });
        }

        // Set recent items
        setRecentRequests(recReq?.data?.items || []);
        setRecentTransfers(transList?.data?.items || []);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    loadDashboardData();

    return () => {
      mounted = false;
    };
  }, [isAuthenticated, isCollegeRep, isPlatformAdmin]);

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Welcome Banner */}
      <section className="relative overflow-hidden rounded-2xl border border-ui-border bg-gradient-to-r from-blue-600/10 via-indigo-600/5 to-transparent p-6 sm:p-8">
        <div className="max-w-2xl">
          <div className="flex items-center gap-2 text-xs font-bold tracking-wider text-blue-600 dark:text-blue-400 uppercase mb-2">
            <span>CAMPUSCYCLE</span>
            <span>•</span>
            <span>
              {isAuthenticated
                ? isPlatformAdmin
                  ? 'GLOBAL ADMINISTRATOR PORTAL'
                  : college?.name || 'COLLEGE WORKSPACE'
                : 'INTER-COLLEGE RESOURCE NETWORK'}
            </span>
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            {isAuthenticated
              ? `Welcome back, ${user?.name || 'User'}`
              : 'Resource Sharing & Transfer Platform for Higher Education'}
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            {isAuthenticated
              ? isPlatformAdmin
                ? 'Manage college verifications, resolve transfer disputes, and maintain platform integrity.'
                : `Manage listings, incoming requests, inventory reservations, and inter-college shipments for ${college?.name}.`
              : 'Connect your college to list educational equipment, request available resources, and coordinate verifiable inter-college transfers.'}
          </p>

          {!isAuthenticated && (
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={onOpenLogin}
                className="py-2.5 px-5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold shadow-lg shadow-blue-500/20 transition-all"
              >
                Sign In to Account
              </button>
              <button
                type="button"
                onClick={onOpenRegister}
                className="py-2.5 px-5 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-800 dark:text-white border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-semibold shadow-sm transition-all"
              >
                Register Your College
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Verification Status Banner if pending */}
      {isAuthenticated && college?.verification_status === 'pending' && (
        <section className="p-4 rounded-xl border border-amber-200 dark:border-amber-800/60 bg-amber-50 dark:bg-amber-950/30 flex items-start gap-3">
          <Clock3 className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-800 dark:text-amber-200">
            <h4 className="font-bold">Institution Verification Pending</h4>
            <p className="mt-0.5 leading-relaxed">
              Your college registration is currently under review by the Platform Administrator. You can browse the
              marketplace, but creating listings, submitting requests, and managing transfers will be enabled once your
              institution is verified.
            </p>
          </div>
        </section>
      )}

      {/* Metrics Row */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: 'Marketplace Resources',
            value: stats.activeListings,
            icon: ShoppingBag,
            color: 'blue',
            link: 'Marketplace',
          },
          {
            label: 'Pending Requests',
            value: stats.pendingRequests,
            icon: BookOpen,
            color: 'amber',
            link: 'My Requests',
          },
          {
            label: 'Active Transfers',
            value: stats.activeTransfers,
            icon: Truck,
            color: 'indigo',
            link: 'Transfers',
          },
          {
            label: isCollegeRep ? 'Available Stock (Units)' : 'Tracked Institutions',
            value: isCollegeRep ? stats.inventoryAvailable : (stats.trackedColleges || stats.activeListings),
            icon: isCollegeRep ? Computer : Building2,
            color: 'emerald',
            link: isCollegeRep ? 'Inventory' : 'College Verification',
          },
        ].map((item) => {
          const Icon = item.icon;
          const colors = {
            blue: 'bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400',
            amber: 'bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400',
            indigo: 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400',
            emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400',
          };

          return (
            <article
              key={item.label}
              onClick={() => onNavigate(item.link)}
              className="cursor-pointer rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm transition hover:shadow-md hover:border-blue-500/40"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-ui-text-secondary">{item.label}</p>
                <div className={`p-2.5 rounded-xl ${colors[item.color]}`}>
                  <Icon size={19} />
                </div>
              </div>
              <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                {isLoading ? <Loader2 className="w-6 h-6 animate-spin text-slate-400" /> : item.value}
              </p>
            </article>
          );
        })}
      </section>

      {/* Quick Actions & Recent Activity */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Quick Links */}
        <section className="rounded-2xl border border-ui-border bg-ui-surface p-6 shadow-sm space-y-4">
          <h2 className="font-display text-base font-bold text-slate-900 dark:text-white">Quick Actions</h2>
          <div className="space-y-2.5">
            <button
              onClick={() => onNavigate('Marketplace')}
              className="w-full flex items-center justify-between p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 hover:bg-blue-50 dark:hover:bg-blue-950/30 text-left transition-colors group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400">
                  <ShoppingBag size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                    Explore Marketplace
                  </h3>
                  <p className="text-xs text-slate-500">Discover equipment and books across colleges</p>
                </div>
              </div>
              <ArrowRight size={16} className="text-slate-400 group-hover:translate-x-0.5 transition-transform" />
            </button>

            {isCollegeRep && (
              <>
                <button
                  onClick={() => onNavigate('My Listings')}
                  className="w-full flex items-center justify-between p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 text-left transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400">
                      <Plus size={18} />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400">
                        Create Resource Listing
                      </h3>
                      <p className="text-xs text-slate-500">Share equipment, books or lab assets</p>
                    </div>
                  </div>
                  <ArrowRight size={16} className="text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </button>

                <button
                  onClick={() => onNavigate('Transfers')}
                  className="w-full flex items-center justify-between p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 hover:bg-indigo-50 dark:hover:bg-indigo-950/30 text-left transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400">
                      <Truck size={18} />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                        Manage Transfers
                      </h3>
                      <p className="text-xs text-slate-500">Track shipments and inspect deliveries</p>
                    </div>
                  </div>
                  <ArrowRight size={16} className="text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </>
            )}

            {isPlatformAdmin && (
              <>
                <button
                  onClick={() => onNavigate('College Verification')}
                  className="w-full flex items-center justify-between p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 hover:bg-blue-50 dark:hover:bg-blue-950/30 text-left transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400">
                      <Building2 size={18} />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900 dark:text-white group-hover:text-blue-600">
                        Review College Onboarding
                      </h3>
                      <p className="text-xs text-slate-500">Approve or reject pending institutions</p>
                    </div>
                  </div>
                  <ArrowRight size={16} className="text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </button>

                <button
                  onClick={() => onNavigate('Transfer Disputes')}
                  className="w-full flex items-center justify-between p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 hover:bg-amber-50 dark:hover:bg-amber-950/30 text-left transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400">
                      <AlertCircle size={18} />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900 dark:text-white group-hover:text-amber-600">
                        Transfer Disputes
                      </h3>
                      <p className="text-xs text-slate-500">Review discrepancies and record settlements</p>
                    </div>
                  </div>
                  <ArrowRight size={16} className="text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </>
            )}
          </div>
        </section>

        {/* Recent Activity */}
        <section className="lg:col-span-2 rounded-2xl border border-ui-border bg-ui-surface p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-base font-bold text-slate-900 dark:text-white">Recent Workflows</h2>
            <button
              onClick={() => onNavigate(isCollegeRep ? 'My Requests' : 'Transfers')}
              className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline"
            >
              View all
            </button>
          </div>

          {!isAuthenticated ? (
            <div className="py-10 text-center text-slate-500 text-xs">
              <CheckCircle2 size={32} className="mx-auto text-blue-500 mb-2 opacity-60" />
              Sign in to view live request and transfer status updates for your institution.
            </div>
          ) : recentRequests.length === 0 && recentTransfers.length === 0 ? (
            <div className="py-10 text-center text-slate-500 text-xs">
              No recent workflows recorded yet. Browse the marketplace or create a listing to begin.
            </div>
          ) : (
            <div className="space-y-3">
              {recentRequests.map((req) => (
                <div
                  key={`req-${req.id}`}
                  onClick={() => onNavigate('My Requests')}
                  className="cursor-pointer p-3.5 rounded-xl border border-slate-100 dark:border-slate-700/80 bg-slate-50/50 dark:bg-slate-900/30 flex items-center justify-between gap-3 hover:bg-slate-100/60 dark:hover:bg-slate-800 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400">
                      <BookOpen size={16} />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                        Request #{req.id} • {req.request_type.replace('_', ' ')}
                      </h4>
                      <p className="text-[11px] text-slate-500 truncate max-w-xs">{req.purpose}</p>
                    </div>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full capitalize bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
                    {req.status}
                  </span>
                </div>
              ))}

              {recentTransfers.map((t) => (
                <div
                  key={`trans-${t.id}`}
                  onClick={() => onNavigate('Transfers')}
                  className="cursor-pointer p-3.5 rounded-xl border border-slate-100 dark:border-slate-700/80 bg-slate-50/50 dark:bg-slate-900/30 flex items-center justify-between gap-3 hover:bg-slate-100/60 dark:hover:bg-slate-800 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400">
                      <Truck size={16} />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                        Transfer Batch #{t.id} • {t.quantity} units
                      </h4>
                      <p className="text-[11px] text-slate-500 truncate max-w-xs">
                        Leg: {t.transfer_leg.replace('_', ' ')}
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
                    {t.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default DashboardView;
