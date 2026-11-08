import React, { useEffect, useState, useCallback } from 'react';
import { Scale, AlertTriangle, History, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import { transfersApi } from '../../api/transfers';
import { DisputeResolutionModal } from '../modals/DisputeResolutionModal';
import { TransferHistoryModal } from '../modals/TransferHistoryModal';

export const DisputeManagementView = ({ onShowToast }) => {
  const [disputes, setDisputes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTransfer, setSelectedTransfer] = useState(null);
  const [historyTransferId, setHistoryTransferId] = useState(null);

  const fetchDisputedTransfers = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await transfersApi.listTransfers({ status: 'disputed', page_size: 50 });
      setDisputes(res?.data?.items || []);
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Error',
        message: err.message || 'Failed to load disputed transfers.',
      });
    } finally {
      setIsLoading(false);
    }
  }, [onShowToast]);

  useEffect(() => {
    fetchDisputedTransfers();
  }, [fetchDisputedTransfers]);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display text-slate-900 dark:text-white flex items-center gap-2.5">
            <Scale className="w-7 h-7 text-indigo-600 dark:text-indigo-400" />
            Transfer Dispute Resolution
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Review delivery discrepancies, report findings, and record binding dispute settlements.
          </p>
        </div>

        <span className="text-xs px-3 py-1.5 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-lg font-semibold flex items-center gap-1.5">
          <AlertTriangle className="w-4 h-4 text-amber-600" />
          {disputes.length} Active Disputes
        </span>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mr-3 text-indigo-600" />
          <span className="text-sm font-medium">Loading disputes...</span>
        </div>
      ) : disputes.length === 0 ? (
        <div className="p-12 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
          <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800 dark:text-white">All Transfers Clear</h3>
          <p className="text-xs text-slate-500 mt-1">There are currently no active transfer disputes requiring review.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {disputes.map((transfer) => (
            <div
              key={transfer.id}
              className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm space-y-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
                    Batch #{transfer.id} • Request #{transfer.request_id}
                  </span>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white mt-0.5">
                    Batch Quantity: {transfer.quantity} units
                  </h3>
                </div>
                <span className="px-2.5 py-1 bg-amber-100 dark:bg-amber-900/60 text-amber-700 dark:text-amber-300 text-xs font-bold rounded-full uppercase tracking-wider">
                  Disputed
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-xl text-center text-xs">
                <div>
                  <span className="text-slate-400 block mb-0.5">Verified Good</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                    {transfer.quantity_received_good ?? '-'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">Damaged</span>
                  <span className="font-bold text-rose-600 dark:text-rose-400 text-sm">
                    {transfer.quantity_damaged ?? 0}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">Missing</span>
                  <span className="font-bold text-amber-600 dark:text-amber-400 text-sm">
                    {transfer.quantity_missing ?? 0}
                  </span>
                </div>
              </div>

              {transfer.receipt_confirmation && (
                <div className="text-xs text-slate-600 dark:text-slate-300 bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200/50 dark:border-amber-800/50 p-3 rounded-xl">
                  <span className="font-semibold block text-slate-700 dark:text-slate-200 mb-0.5">Receiver Inspection Note:</span>
                  {transfer.receipt_confirmation}
                </div>
              )}

              <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-700">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Received: {transfer.received_at ? new Date(transfer.received_at).toLocaleDateString() : 'N/A'}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setHistoryTransferId(transfer.id)}
                    className="p-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1"
                    title="Audit trail"
                  >
                    <History className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setSelectedTransfer(transfer)}
                    className="py-1.5 px-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors"
                  >
                    Resolve Dispute
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedTransfer && (
        <DisputeResolutionModal
          isOpen={true}
          transfer={selectedTransfer}
          onClose={() => setSelectedTransfer(null)}
          onSuccess={() => {
            onShowToast?.({
              type: 'success',
              title: 'Dispute Resolved',
              message: 'The dispute has been resolved and inventory invariants updated.',
            });
            fetchDisputedTransfers();
          }}
        />
      )}

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

export default DisputeManagementView;
