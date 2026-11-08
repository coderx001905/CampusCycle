import React, { useEffect, useState, useCallback } from 'react';
import {
  Search,
  PackageCheck,
  Send,
  History,
  AlertTriangle,
  Loader2,
  Calendar,
} from 'lucide-react';
import { transfersApi } from '../api/transfers';
import { useAuth } from '../context/AuthContext';
import { ReceiptModal } from '../components/modals/ReceiptModal';
import { TransferHistoryModal } from '../components/modals/TransferHistoryModal';

export const TransfersView = ({ onShowToast, onNavigate }) => {
  const { college, isAuthenticated, isPlatformAdmin } = useAuth();
  const [transfers, setTransfers] = useState([]);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('All');
  const [search, setSearch] = useState('');

  // Modals & Action States
  const [receiptModalTransfer, setReceiptModalTransfer] = useState(null);
  const [historyTransferId, setHistoryTransferId] = useState(null);
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const fetchTransfers = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const params = { page, page_size: 50 };
      if (statusFilter !== 'All') params.status = statusFilter;

      const res = await transfersApi.listTransfers(params);
      setTransfers(res?.data?.items || []);
      setTotal(res?.data?.total || 0);
    } catch (err) {
      console.error('Error fetching transfers:', err);
    } finally {
      setIsLoading(false);
    }
  }, [page, statusFilter, isAuthenticated]);

  useEffect(() => {
    fetchTransfers();
  }, [fetchTransfers]);

  const handleDispatch = async (transferId) => {
    setActionLoadingId(transferId);
    try {
      await transfersApi.dispatchTransfer(transferId, {
        dispatch_notes: 'Dispatched via verified campus logistics courier.',
      });
      onShowToast?.({
        type: 'success',
        title: 'Batch Dispatched',
        message: `Transfer Batch #${transferId} has been dispatched.`,
      });
      await fetchTransfers();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Dispatch Failed',
        message: err.response?.data?.detail || err.message || 'Could not record dispatch.',
      });
    } finally {
      setActionLoadingId(null);
    }
  };

  const filteredTransfers = transfers.filter((t) => {
    const matchesSearch =
      !search.trim() ||
      String(t.id).includes(search) ||
      String(t.request_id).includes(search) ||
      (t.dispatch_notes && t.dispatch_notes.toLowerCase().includes(search.toLowerCase())) ||
      (t.receipt_confirmation && t.receipt_confirmation.toLowerCase().includes(search.toLowerCase()));

    return matchesSearch;
  });

  const statusStyles = {
    pending_dispatch: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
    in_transit: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
    delivered: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300',
    completed: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    cancelled: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400',
    disputed: 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300',
    cancellation_pending: 'bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300',
  };

  return (
    <div className="space-y-7 animate-in fade-in duration-200">
      {/* Header */}
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-ui-text-muted">
            <span>WORKSPACE</span>
            <span>/</span>
            <span className="text-ui-accent">LOGISTICS & TRANSFERS</span>
          </div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-[34px]">
            Transfer Tracking & Receipts
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-ui-text-secondary">
            Coordinate inter-college dispatches, inspect verified receipts, track shipment status histories, and review
            disputes.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onNavigate('My Requests')}
          className="py-2.5 px-4 bg-ui-accent hover:bg-ui-accent-hover text-white rounded-xl text-xs font-semibold shadow-md transition"
        >
          View Approved Requests
        </button>
      </section>

      {/* Filter and Search Bar */}
      <section className="rounded-2xl border border-ui-border bg-ui-surface p-4 sm:p-5 shadow-sm flex flex-col sm:flex-row gap-3 justify-between items-stretch sm:items-center">
        <div className="flex items-center gap-1.5 flex-wrap">
          {['All', 'pending_dispatch', 'in_transit', 'completed', 'disputed', 'cancelled'].map((st) => (
            <button
              key={st}
              onClick={() => {
                setStatusFilter(st);
                setPage(1);
              }}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold capitalize transition ${
                statusFilter === st
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by transfer ID or notes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full sm:w-60 pl-9 pr-3 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white"
          />
        </div>
      </section>

      {/* Transfers Table / Cards */}
      <section className="overflow-hidden rounded-2xl border border-ui-border bg-ui-surface shadow-sm">
        <div className="border-b border-ui-border px-5 py-4 flex items-center justify-between">
          <h2 className="font-display text-base font-bold text-slate-900 dark:text-white">Active Transfer Shipments</h2>
          <span className="text-xs text-slate-500">{filteredTransfers.length} records</span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin mr-3 text-blue-600" />
            <span className="text-sm font-medium">Loading transfer records...</span>
          </div>
        ) : filteredTransfers.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-sm">
            No transfer shipments recorded matching this filter.
          </div>
        ) : (
          <div className="divide-y divide-ui-border">
            {filteredTransfers.map((t) => {
              const isSender = college?.id === t.source_college_id;
              const isReceiver = college?.id === t.destination_college_id;

              return (
                <article
                  key={t.id}
                  className="p-5 hover:bg-ui-subtle/40 transition-colors flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-bold text-slate-900 dark:text-white text-base">
                        Batch #{t.id}
                      </span>
                      <span className="text-xs text-slate-400">• Request #{t.request_id}</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        Leg: {t.transfer_leg.replace('_', ' ')}
                      </span>
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          statusStyles[t.status] || 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {t.status.replace('_', ' ')}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 dark:text-slate-300">
                      <span>
                        Quantity: <strong>{t.quantity} units</strong>
                      </span>
                      <span>•</span>
                      <span>From College #{t.source_college_id}</span>
                      <span>→</span>
                      <span>To College #{t.destination_college_id}</span>
                      {t.pickup_or_delivery_date && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-1 text-slate-400">
                            <Calendar size={13} />
                            {new Date(t.pickup_or_delivery_date).toLocaleDateString()}
                          </span>
                        </>
                      )}
                    </div>

                    {t.dispatch_notes && (
                      <p className="text-xs text-slate-500 italic bg-ui-subtle p-2 rounded-lg inline-block">
                        Dispatch note: {t.dispatch_notes}
                      </p>
                    )}

                    {t.status === 'disputed' && (
                      <div className="flex items-center gap-2 text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 p-2 rounded-lg border border-rose-200 dark:border-rose-900/60 font-semibold">
                        <AlertTriangle size={15} />
                        <span>
                          Delivery Discrepancy Reported • Good: {t.quantity_received_good ?? '-'}, Damaged: {t.quantity_damaged ?? 0}, Missing: {t.quantity_missing ?? 0}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                    <button
                      onClick={() => setHistoryTransferId(t.id)}
                      className="p-2 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-xs font-semibold flex items-center gap-1 transition"
                      title="View audit timeline"
                    >
                      <History size={16} />
                    </button>

                    {/* Dispatch action for sender */}
                    {(isSender || isPlatformAdmin) && t.status === 'pending_dispatch' && (
                      <button
                        onClick={() => handleDispatch(t.id)}
                        disabled={actionLoadingId === t.id}
                        className="py-1.5 px-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-sm flex items-center gap-1.5 transition disabled:opacity-50"
                      >
                        {actionLoadingId === t.id ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : (
                          <Send size={13} />
                        )}
                        <span>Dispatch Batch</span>
                      </button>
                    )}

                    {/* Receipt inspection action for receiver */}
                    {(isReceiver || isPlatformAdmin) && (t.status === 'in_transit' || t.status === 'delivered') && (
                      <button
                        onClick={() => setReceiptModalTransfer(t)}
                        className="py-1.5 px-3.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm flex items-center gap-1.5 transition"
                      >
                        <PackageCheck size={14} />
                        <span>Inspect & Confirm Receipt</span>
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* Receipt Modal */}
      {receiptModalTransfer && (
        <ReceiptModal
          isOpen={true}
          transfer={receiptModalTransfer}
          onClose={() => setReceiptModalTransfer(null)}
          onSuccess={(outcome) => {
            onShowToast?.({
              type: outcome === 'disputed' ? 'info' : 'success',
              title: outcome === 'disputed' ? 'Discrepancy Reported' : 'Receipt Confirmed',
              message:
                outcome === 'disputed'
                  ? 'Discrepancies reported; this transfer is now marked Disputed for admin resolution.'
                  : 'Items verified in good condition; inventory updated.',
            });
            fetchTransfers();
          }}
        />
      )}

      {/* History Modal */}
      {historyTransferId && (
        <TransferHistoryModal
          isOpen={true}
          transferId={historyTransferId}
          onClose={() => setHistoryTransferId(null)}
        />
      )}
    </div>
  );
};

export default TransfersView;
