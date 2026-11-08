import React, { useEffect, useState } from 'react';
import { History, X, Clock, Loader2, ArrowRight } from 'lucide-react';
import { transfersApi } from '../../api/transfers';

export const TransferHistoryModal = ({ isOpen, transferId, onClose }) => {
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!isOpen || !transferId) return;

    let mounted = true;
    setIsLoading(true);
    setErrorMsg('');

    transfersApi
      .getTransferHistory(transferId)
      .then((res) => {
        if (mounted) {
          setHistory(res?.data?.items || []);
        }
      })
      .catch((err) => {
        if (mounted) {
          setErrorMsg(err.message || 'Failed to load transfer history.');
        }
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [isOpen, transferId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg p-6 bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[85vh] flex flex-col">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-5 shrink-0">
          <div className="p-3 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl">
            <History className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Transfer Audit History</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Transfer Batch #{transferId}</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto pr-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin mr-2" />
              <span className="text-sm">Loading audit trail...</span>
            </div>
          ) : errorMsg ? (
            <div className="p-4 bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 rounded-xl text-xs">
              {errorMsg}
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-sm">
              No status transitions recorded yet.
            </div>
          ) : (
            <div className="relative border-l border-slate-200 dark:border-slate-700 ml-4 space-y-6 py-2">
              {history.map((item) => (
                <div key={item.id} className="relative pl-6">
                  <div className="absolute -left-1.5 top-1.5 w-3 h-3 rounded-full bg-blue-600 border-2 border-white dark:border-slate-800" />
                  <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{new Date(item.changed_at).toLocaleString()}</span>
                    <span className="text-slate-300 dark:text-slate-600">•</span>
                    <span className="capitalize font-medium text-slate-600 dark:text-slate-300">{item.actor_type.replace('_', ' ')}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
                    <span className="text-slate-500 font-normal">{item.previous_status || 'Initialized'}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-blue-600 dark:text-blue-400 uppercase text-xs font-bold tracking-wider">
                      {item.new_status}
                    </span>
                  </div>
                  {item.notes && (
                    <p className="mt-1.5 text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/40 p-2.5 rounded-lg border border-slate-200/60 dark:border-slate-700/60">
                      {item.notes}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-slate-200 dark:border-slate-700 mt-4 shrink-0 flex justify-end">
          <button
            onClick={onClose}
            className="py-2 px-5 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default TransferHistoryModal;
