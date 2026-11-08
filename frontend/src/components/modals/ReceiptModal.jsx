import React, { useState } from 'react';
import { PackageCheck, X, AlertTriangle, Loader2 } from 'lucide-react';
import { transfersApi } from '../../api/transfers';

export const ReceiptModal = ({ isOpen, transfer, onClose, onSuccess }) => {
  const [goodQty, setGoodQty] = useState('');
  const [damagedQty, setDamagedQty] = useState(0);
  const [missingQty, setMissingQty] = useState(0);
  const [notes, setNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !transfer) return null;

  const totalExpected = transfer.quantity;
  const currentTotal = (Number(goodQty) || 0) + (Number(damagedQty) || 0) + (Number(missingQty) || 0);
  const hasDiscrepancy = Number(damagedQty) > 0 || Number(missingQty) > 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    const good = Number(goodQty);
    const damaged = Number(damagedQty) || 0;
    const missing = Number(missingQty) || 0;

    if (good < 0 || damaged < 0 || missing < 0) {
      setErrorMsg('Quantities cannot be negative.');
      return;
    }

    if (good + damaged + missing !== totalExpected) {
      setErrorMsg(`Total verified quantity (${good + damaged + missing}) must equal batch quantity (${totalExpected}).`);
      return;
    }

    setIsSubmitting(true);
    try {
      await transfersApi.confirmReceipt(transfer.id, {
        quantity_received_good: good,
        quantity_damaged: damaged,
        quantity_missing: missing,
        receipt_confirmation: notes.trim() || undefined,
      });
      onSuccess(hasDiscrepancy ? 'disputed' : 'completed');
      onClose();
    } catch (err) {
      setErrorMsg(
        err.response?.data?.error?.message ||
        err.response?.data?.detail ||
        'Failed to record receipt.'
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
          <div className="p-3 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl">
            <PackageCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Inspect & Confirm Receipt</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Transfer Batch #{transfer.id} • Expected: {totalExpected} units</p>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl text-xs text-rose-600 dark:text-rose-400">
            {errorMsg}
          </div>
        )}

        {hasDiscrepancy && (
          <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl flex items-start gap-2 text-xs text-amber-700 dark:text-amber-300">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
            <span>Reporting damaged or missing items will mark this transfer batch as <strong>Disputed</strong> for Platform Admin review.</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Good Condition *
              </label>
              <input
                type="number"
                min="0"
                max={totalExpected}
                required
                value={goodQty}
                onChange={(e) => setGoodQty(e.target.value)}
                placeholder="0"
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Damaged Items
              </label>
              <input
                type="number"
                min="0"
                max={totalExpected}
                value={damagedQty}
                onChange={(e) => setDamagedQty(e.target.value)}
                placeholder="0"
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Missing Items
              </label>
              <input
                type="number"
                min="0"
                max={totalExpected}
                value={missingQty}
                onChange={(e) => setMissingQty(e.target.value)}
                placeholder="0"
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
              />
            </div>
          </div>

          <div className="flex justify-between items-center px-1 text-xs text-slate-500 dark:text-slate-400">
            <span>Total Accounted: <strong>{currentTotal} / {totalExpected}</strong></span>
            {currentTotal !== totalExpected && (
              <span className="text-rose-500 font-medium">Difference: {totalExpected - currentTotal}</span>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Inspection Notes / Confirmation Comment
            </label>
            <textarea
              rows="2"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Package received in good condition, seals intact."
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
              disabled={isSubmitting || currentTotal !== totalExpected}
              className="flex-1 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium shadow-md disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <span>Confirm Receipt</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ReceiptModal;
