import React, { useState } from 'react';
import { Scale, X, Loader2 } from 'lucide-react';
import { transfersApi } from '../../api/transfers';

export const DisputeResolutionModal = ({ isOpen, transfer, onClose, onSuccess }) => {
  const [outcome, setOutcome] = useState('accept_report');
  const [resolutionText, setResolutionText] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !transfer) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!resolutionText.trim()) {
      setErrorMsg('Please enter a detailed dispute resolution rationale.');
      return;
    }

    setIsSubmitting(true);
    try {
      await transfersApi.resolveDispute(transfer.id, {
        dispute_outcome: outcome,
        dispute_resolution: resolutionText.trim(),
      });
      onSuccess();
      onClose();
    } catch (err) {
      setErrorMsg(
        err.response?.data?.error?.message ||
        err.response?.data?.detail ||
        'Failed to resolve dispute.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg p-6 bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="p-3 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-xl">
            <Scale className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Resolve Transfer Dispute</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Transfer #{transfer.id} • Damaged: {transfer.quantity_damaged || 0}, Missing: {transfer.quantity_missing || 0}</p>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl text-xs text-rose-600 dark:text-rose-400">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Resolution Outcome *
            </label>
            <select
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
            >
              <option value="accept_report">Accept Inspection Report (Deduct good items, write off damaged/missing)</option>
              <option value="replacement_approved">Approve Replacement (Authorizes sender to dispatch replacement batch)</option>
              <option value="claim_rejected">Reject Claim (Uphold original batch without automatic write-off)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Detailed Resolution Rationale *
            </label>
            <textarea
              rows="4"
              required
              value={resolutionText}
              onChange={(e) => setResolutionText(e.target.value)}
              placeholder="Document the investigation findings and instructions for both institutions..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 px-4 border border-slate-300 dark:border-slate-600 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-medium shadow-md disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Recording...</span>
                </>
              ) : (
                <span>Finalize Resolution</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DisputeResolutionModal;
