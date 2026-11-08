import React, { useEffect, useState, useCallback } from 'react';
import {
  BookOpen,
  Search,
  CheckCircle2,
  XCircle,
  Truck,
  DollarSign,
  Loader2,
  Package,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { requestsApi } from '../api/requests';
import { TransferCreateModal } from '../components/modals/TransferCreateModal';

export const MyRequestsView = ({ onShowToast, onNavigate }) => {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState('received'); // 'received' | 'mine'
  const [requests, setRequests] = useState([]);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('All');
  const [search, setSearch] = useState('');

  // Interactive action modals
  const [approvalModalRequest, setApprovalModalRequest] = useState(null);
  const [approvedQuantity, setApprovedQuantity] = useState('');
  const [rejectionModalRequest, setRejectionModalRequest] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [cancelModalRequest, setCancelModalRequest] = useState(null);
  const [cancelReason, setCancelReason] = useState('');
  const [transferBatchRequest, setTransferBatchRequest] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchRequests = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      let res;
      if (activeTab === 'received') {
        res = await requestsApi.getReceived(page, 50);
      } else {
        res = await requestsApi.getMine(page, 50);
      }
      setRequests(res?.data?.items || []);
      setTotal(res?.data?.total || 0);
    } catch (err) {
      console.error('Error fetching requests:', err);
    } finally {
      setIsLoading(false);
    }
  }, [activeTab, page, isAuthenticated]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const handleApprove = async (e) => {
    e.preventDefault();
    if (!approvalModalRequest) return;

    setActionLoading(true);
    try {
      const qty =
        approvalModalRequest.request_type === 'donation' && approvedQuantity
          ? Number(approvedQuantity)
          : null;

      await requestsApi.approveRequest(approvalModalRequest.id, qty);
      onShowToast?.({
        type: 'success',
        title: 'Request Approved',
        message: `Request #${approvalModalRequest.id} has been approved and inventory reserved.`,
      });
      setApprovalModalRequest(null);
      await fetchRequests();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Approval Failed',
        message: err.response?.data?.detail || err.response?.data?.error?.message || 'Could not approve request.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (e) => {
    e.preventDefault();
    if (!rejectionModalRequest || !rejectionReason.trim()) return;

    setActionLoading(true);
    try {
      await requestsApi.rejectRequest(rejectionModalRequest.id, rejectionReason.trim());
      onShowToast?.({
        type: 'success',
        title: 'Request Rejected',
        message: `Request #${rejectionModalRequest.id} has been rejected.`,
      });
      setRejectionModalRequest(null);
      setRejectionReason('');
      await fetchRequests();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Rejection Failed',
        message: err.response?.data?.detail || err.response?.data?.error?.message || 'Could not reject request.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmPurchase = async (requestId) => {
    setActionLoading(true);
    try {
      await requestsApi.confirmPurchase(requestId);
      onShowToast?.({
        type: 'success',
        title: 'Purchase Confirmed',
        message: 'Your purchase intention is confirmed; stock is now officially reserved for transfer.',
      });
      await fetchRequests();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Confirmation Failed',
        message:
          err.response?.data?.detail ||
          err.response?.data?.error?.message ||
          'Failed to confirm purchase. The seller may have insufficient stock.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelRequest = async (e) => {
    e.preventDefault();
    if (!cancelModalRequest || !cancelReason.trim()) return;

    setActionLoading(true);
    try {
      await requestsApi.cancelRequest(cancelModalRequest.id, cancelReason.trim());
      onShowToast?.({
        type: 'success',
        title: 'Cancellation Requested',
        message: 'Your cancellation request has been submitted for review.',
      });
      setCancelModalRequest(null);
      setCancelReason('');
      await fetchRequests();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Cancellation Failed',
        message: err.response?.data?.detail || err.response?.data?.error?.message || 'Could not cancel request.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancellationDecision = async (requestId, decision) => {
    setActionLoading(true);
    try {
      await requestsApi.decideCancellation(requestId, decision);
      onShowToast?.({
        type: 'success',
        title: 'Cancellation Decision Saved',
        message: `The cancellation request was ${decision}.`,
      });
      await fetchRequests();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Decision Failed',
        message: err.response?.data?.detail || err.response?.data?.error?.message || 'Could not record decision.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const filteredRequests = requests.filter((req) => {
    const matchesStatus =
      statusFilter === 'All' || req.status.toLowerCase() === statusFilter.toLowerCase();
    const matchesSearch =
      !search.trim() ||
      req.purpose.toLowerCase().includes(search.toLowerCase()) ||
      String(req.id).includes(search);
    return matchesStatus && matchesSearch;
  });

  const statusStyles = {
    pending: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
    approved: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    purchase_confirmed: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
    partially_fulfilled: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300',
    completed: 'bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300',
    rejected: 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300',
    cancelled: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400',
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
            <span className="text-ui-accent">REQUESTS</span>
          </div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-[34px]">
            Resource Requests & Inquiries
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-ui-text-secondary">
            Process inquiries received for your inventory and track applications you have submitted to other colleges.
          </p>
        </div>
      </section>

      {/* Tabs & Filters */}
      <section className="rounded-2xl border border-ui-border bg-ui-surface p-4 sm:p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap gap-2 border-b border-ui-border/60 pb-4">
          <button
            type="button"
            onClick={() => {
              setActiveTab('received');
              setPage(1);
            }}
            className={`px-5 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
              activeTab === 'received'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                : 'bg-ui-subtle text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span>Received Requests</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/20">
              Inbound
            </span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab('mine');
              setPage(1);
            }}
            className={`px-5 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
              activeTab === 'mine'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                : 'bg-ui-subtle text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span>Sent Requests</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/20">
              Outbound
            </span>
          </button>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-between items-stretch sm:items-center">
          <div className="flex items-center gap-1.5 flex-wrap">
            {['All', 'pending', 'approved', 'purchase_confirmed', 'completed', 'rejected', 'cancelled'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition ${
                  statusFilter === st
                    ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200'
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
              placeholder="Search by purpose, ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full sm:w-56 pl-9 pr-3 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white"
            />
          </div>
        </div>
      </section>

      {/* Requests List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mr-3 text-blue-600" />
          <span className="text-sm font-medium">Loading requests...</span>
        </div>
      ) : filteredRequests.length === 0 ? (
        <div className="p-16 text-center bg-ui-surface rounded-2xl border border-ui-border">
          <BookOpen className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800 dark:text-white">No Requests Found</h3>
          <p className="text-xs text-slate-500 mt-1">There are no {activeTab} requests matching this view.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredRequests.map((req) => (
            <article
              key={req.id}
              className="bg-ui-surface rounded-2xl border border-ui-border p-5 shadow-sm hover:border-blue-500/30 transition-all space-y-4"
            >
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400">
                    <Package size={20} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-slate-900 dark:text-white text-base">
                        Request #{req.id} • Resource #{req.resource_id}
                      </h3>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {req.request_type.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Requested: <strong>{req.requested_quantity} units</strong>
                      {req.approved_quantity != null && (
                        <span> • Approved: <strong className="text-emerald-600">{req.approved_quantity} units</strong></span>
                      )}
                      <span> • Date: {new Date(req.created_at).toLocaleDateString()}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                      statusStyles[req.status] || 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {req.status.replace('_', ' ')}
                  </span>
                </div>
              </div>

              {/* Purpose and message */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-ui-subtle p-3.5 rounded-xl">
                <div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    Academic Purpose / Need:
                  </span>
                  <p className="text-slate-600 dark:text-slate-400 leading-relaxed">{req.purpose}</p>
                </div>
                {req.message && (
                  <div>
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                      Applicant Message:
                    </span>
                    <p className="text-slate-600 dark:text-slate-400 leading-relaxed">{req.message}</p>
                  </div>
                )}
                {req.offered_resource_id != null && (
                  <div className="md:col-span-2 pt-2 border-t border-slate-200/50 dark:border-slate-700/50 text-indigo-600 dark:text-indigo-400 font-semibold">
                    Proposed Exchange: Resource #{req.offered_resource_id} ({req.offered_quantity} units offered)
                  </div>
                )}
                {req.rejection_reason && (
                  <div className="md:col-span-2 pt-2 border-t border-rose-200 dark:border-rose-900/50 text-rose-600 dark:text-rose-400">
                    <span className="font-bold">Rejection Reason:</span> {req.rejection_reason}
                  </div>
                )}
                {req.cancellation_reason && (
                  <div className="md:col-span-2 pt-2 border-t border-orange-200 dark:border-orange-900/50 text-orange-600 dark:text-orange-400">
                    <span className="font-bold">Cancellation Request:</span> {req.cancellation_reason}
                  </div>
                )}
              </div>

              {/* Workflow Actions */}
              <div className="flex flex-wrap items-center justify-end gap-2.5 pt-2 border-t border-ui-border/60">
                {/* Received Actions for Pending */}
                {activeTab === 'received' && req.status === 'pending' && (
                  <>
                    <button
                      onClick={() => setRejectionModalRequest(req)}
                      disabled={actionLoading}
                      className="py-1.5 px-3.5 bg-rose-50 hover:bg-rose-100 text-rose-600 dark:bg-rose-950/30 dark:hover:bg-rose-900/50 rounded-xl text-xs font-semibold transition"
                    >
                      Reject Request
                    </button>
                    <button
                      onClick={() => {
                        setApprovalModalRequest(req);
                        setApprovedQuantity(String(req.requested_quantity));
                      }}
                      disabled={actionLoading}
                      className="py-1.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-sm transition"
                    >
                      Approve Request
                    </button>
                  </>
                )}

                {/* Sent Action: Confirm Purchase Intent */}
                {activeTab === 'mine' && req.request_type === 'purchase_enquiry' && req.status === 'approved' && (
                  <button
                    onClick={() => handleConfirmPurchase(req.id)}
                    disabled={actionLoading}
                    className="py-1.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-md flex items-center gap-1.5 transition"
                  >
                    <DollarSign size={14} />
                    <span>Confirm Purchase Intent & Reserve Stock</span>
                  </button>
                )}

                {/* Create Transfer Batch */}
                {(req.status === 'approved' || req.status === 'purchase_confirmed' || req.status === 'partially_fulfilled') && (
                  <button
                    onClick={() => setTransferBatchRequest(req)}
                    disabled={actionLoading}
                    className="py-1.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm flex items-center gap-1.5 transition"
                  >
                    <Truck size={14} />
                    <span>Create Transfer Batch</span>
                  </button>
                )}

                {/* Cancellation review for receiving side */}
                {activeTab === 'received' && req.status === 'cancellation_pending' && (
                  <>
                    <button
                      onClick={() => handleCancellationDecision(req.id, 'rejected')}
                      disabled={actionLoading}
                      className="py-1.5 px-3 bg-slate-100 dark:bg-slate-700 text-xs font-semibold rounded-xl"
                    >
                      Decline Cancellation
                    </button>
                    <button
                      onClick={() => handleCancellationDecision(req.id, 'approved')}
                      disabled={actionLoading}
                      className="py-1.5 px-3 bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold rounded-xl"
                    >
                      Approve Cancellation & Release Stock
                    </button>
                  </>
                )}

                {/* Cancel request button for applicant */}
                {activeTab === 'mine' &&
                  (req.status === 'pending' || req.status === 'approved' || req.status === 'purchase_confirmed') && (
                    <button
                      onClick={() => setCancelModalRequest(req)}
                      disabled={actionLoading}
                      className="py-1.5 px-3 text-slate-500 hover:text-rose-600 rounded-lg text-xs font-semibold"
                    >
                      Request Cancellation
                    </button>
                  )}
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Approval Modal */}
      {approvalModalRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md p-6 bg-ui-surface rounded-2xl shadow-2xl border border-ui-border">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">
              Approve Resource Request #{approvalModalRequest.id}
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Approving this request will atomically reserve inventory.
            </p>

            <form onSubmit={handleApprove} className="space-y-4">
              {approvalModalRequest.request_type === 'donation' ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Approved Quantity * (Max: {approvalModalRequest.requested_quantity})
                  </label>
                  <input
                    type="number"
                    min="1"
                    max={approvalModalRequest.requested_quantity}
                    required
                    value={approvedQuantity}
                    onChange={(e) => setApprovedQuantity(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Donations permit partial quantity approvals.</p>
                </div>
              ) : (
                <div className="p-3 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 rounded-xl text-xs">
                  For {approvalModalRequest.request_type.replace('_', ' ')} requests, approval must equal the full
                  requested quantity ({approvalModalRequest.requested_quantity} units) to satisfy database integrity constraints.
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setApprovalModalRequest(null)}
                  className="flex-1 py-2 px-4 border border-slate-300 dark:border-slate-600 rounded-xl text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="flex-1 py-2 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-md flex items-center justify-center gap-1.5"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 size={15} />}
                  <span>Confirm Approval</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Rejection Modal */}
      {rejectionModalRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md p-6 bg-ui-surface rounded-2xl shadow-2xl border border-ui-border">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">
              Reject Request #{rejectionModalRequest.id}
            </h3>
            <p className="text-xs text-slate-500 mb-4">Provide a reason for declining this request.</p>

            <form onSubmit={handleReject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Reason for Rejection *
                </label>
                <textarea
                  rows="3"
                  required
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g. Currently prioritized for internal departmental lab coursework..."
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setRejectionModalRequest(null)}
                  className="flex-1 py-2 px-4 border border-slate-300 dark:border-slate-600 rounded-xl text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="flex-1 py-2 px-4 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-semibold shadow-md flex items-center justify-center gap-1.5"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle size={15} />}
                  <span>Confirm Rejection</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cancel Request Modal */}
      {cancelModalRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md p-6 bg-ui-surface rounded-2xl shadow-2xl border border-ui-border">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">
              Request Cancellation
            </h3>
            <p className="text-xs text-slate-500 mb-4">Request #{cancelModalRequest.id}</p>

            <form onSubmit={handleCancelRequest} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Cancellation Reason *
                </label>
                <textarea
                  rows="3"
                  required
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="Explain why this request is being cancelled..."
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCancelModalRequest(null)}
                  className="flex-1 py-2 px-4 border border-slate-300 dark:border-slate-600 rounded-xl text-xs font-semibold"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="flex-1 py-2 px-4 bg-orange-600 hover:bg-orange-700 text-white rounded-xl text-xs font-semibold shadow-md"
                >
                  Submit Cancellation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Transfer Batch Modal */}
      {transferBatchRequest && (
        <TransferCreateModal
          isOpen={true}
          request={transferBatchRequest}
          onClose={() => setTransferBatchRequest(null)}
          onSuccess={() => {
            onShowToast?.({
              type: 'success',
              title: 'Transfer Batch Created',
              message: 'The transfer batch has been created in pending dispatch status.',
            });
            fetchRequests();
            onNavigate('Transfers');
          }}
        />
      )}
    </div>
  );
};

export default MyRequestsView;
