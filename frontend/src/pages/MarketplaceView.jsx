import React, { useEffect, useState, useCallback } from 'react';
import {
  ShoppingBag,
  Search,
  Plus,
  Building2,
  X,
  Send,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Package,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { resourcesApi } from '../api/resources';
import { requestsApi } from '../api/requests';

export const MarketplaceView = ({ onNavigate, onOpenLogin, onShowToast }) => {
  const { college, isAuthenticated, isVerifiedCollege } = useAuth();
  const [resources, setResources] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedCondition, setSelectedCondition] = useState('');
  const [selectedTransferType, setSelectedTransferType] = useState('');

  // Selected Resource Modal State
  const [selectedResource, setSelectedResource] = useState(null);
  const [requestedQty, setRequestedQty] = useState(1);
  const [purpose, setPurpose] = useState('');
  const [message, setMessage] = useState('');
  const [offeredResourceId, setOfferedResourceId] = useState('');
  const [offeredQty, setOfferedQty] = useState(1);
  const [myInventory, setMyInventory] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [modalError, setModalError] = useState('');

  const fetchResources = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = {
        page,
        page_size: 24,
      };
      if (search.trim()) params.search = search.trim();
      if (selectedCategory) params.category = selectedCategory;
      if (selectedCondition) params.condition = selectedCondition;
      if (selectedTransferType) params.transfer_type = selectedTransferType;

      const res = await resourcesApi.listResources(params);
      setResources(res?.data?.items || []);
      setTotal(res?.data?.total || 0);
    } catch (err) {
      console.error('Error fetching resources:', err);
    } finally {
      setIsLoading(false);
    }
  }, [page, search, selectedCategory, selectedCondition, selectedTransferType]);

  useEffect(() => {
    fetchResources();
  }, [fetchResources]);

  // Load owned inventory when opening an exchange request
  const openDetailModal = async (resource) => {
    setSelectedResource(resource);
    setRequestedQty(1);
    setPurpose('');
    setMessage('');
    setOfferedResourceId('');
    setOfferedQty(1);
    setSubmitSuccess(false);
    setModalError('');

    if (isAuthenticated && isVerifiedCollege && resource.transfer_type === 'exchange') {
      try {
        const invRes = await resourcesApi.getMyInventory();
        const availableItems = (invRes?.data?.items || []).filter(
          (item) => item.quantity_available > 0 && item.id !== resource.id
        );
        setMyInventory(availableItems);
      } catch (err) {
        console.error('Failed to load owned inventory for exchange:', err);
      }
    }
  };

  const handleRequestSubmit = async (e) => {
    e.preventDefault();
    setModalError('');

    if (!isAuthenticated) {
      setSelectedResource(null);
      onOpenLogin();
      return;
    }

    if (!isVerifiedCollege) {
      setModalError('Your institution must be verified before submitting resource requests.');
      return;
    }

    if (selectedResource.college?.id === college?.id) {
      setModalError('You cannot request resources listed by your own institution.');
      return;
    }

    const qty = Number(requestedQty);
    if (!qty || qty <= 0 || qty > selectedResource.quantity_available) {
      setModalError(`Please request between 1 and ${selectedResource.quantity_available} units.`);
      return;
    }

    if (!purpose.trim()) {
      setModalError('Please state the purpose for requesting this educational resource.');
      return;
    }

    if (selectedResource.transfer_type === 'exchange' && !offeredResourceId) {
      setModalError('Please select a resource from your inventory to offer in exchange.');
      return;
    }

    setIsSubmitting(true);
    try {
      // Backend request_type expects "donation" | "exchange" | "purchase_enquiry"
      let reqType = selectedResource.transfer_type;
      if (reqType === 'sale') reqType = 'purchase_enquiry';

      const payload = {
        resource_id: selectedResource.id,
        request_type: reqType,
        requested_quantity: qty,
        purpose: purpose.trim(),
        message: message.trim() || undefined,
        offered_resource_id: selectedResource.transfer_type === 'exchange' ? Number(offeredResourceId) : undefined,
        offered_quantity: selectedResource.transfer_type === 'exchange' ? Number(offeredQty) : undefined,
      };

      await requestsApi.submitRequest(payload);
      setSubmitSuccess(true);
      onShowToast?.({
        type: 'success',
        title: 'Request Submitted',
        message: 'Your resource request has been transmitted to the listing college.',
      });
      fetchResources();
    } catch (err) {
      setModalError(
        err.response?.data?.error?.message ||
        err.response?.data?.detail ||
        'Failed to submit request.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const typePills = {
    donation: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    exchange: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300',
    sale: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
  };

  return (
    <div className="space-y-7 animate-in fade-in duration-200">
      {/* Header */}
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-ui-text-muted">
            <span>WORKSPACE</span>
            <span>/</span>
            <span className="text-ui-accent">MARKETPLACE</span>
          </div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-[34px]">
            Campus Resource Marketplace
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-ui-text-secondary">
            Discover verified educational equipment, laboratory supplies, and materials shared across participating
            institutions.
          </p>
        </div>

        {isAuthenticated && isVerifiedCollege && (
          <button
            type="button"
            onClick={() => onNavigate('My Listings')}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-ui-accent px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:bg-ui-accent-hover"
          >
            <Plus size={17} />
            List a Resource
          </button>
        )}
      </section>

      {/* Filter and Search Bar */}
      <section className="rounded-2xl border border-ui-border bg-ui-surface p-4 sm:p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ui-text-muted" />
            <input
              type="search"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search by resource title, category, or description..."
              className="h-11 w-full rounded-xl border border-ui-border bg-ui-canvas pl-10 pr-4 text-sm text-ui-text-primary outline-none focus:border-ui-focus"
            />
          </div>

          <div className="grid grid-cols-3 gap-2 sm:w-auto">
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setPage(1);
              }}
              className="h-11 rounded-xl border border-ui-border bg-ui-canvas px-3 text-xs font-semibold text-ui-text-primary outline-none focus:border-ui-focus"
            >
              <option value="">All Categories</option>
              <option value="Books">Books</option>
              <option value="Electronics">Electronics</option>
              <option value="Lab equipment">Lab equipment</option>
              <option value="Study material">Study material</option>
              <option value="Other">Other</option>
            </select>

            <select
              value={selectedTransferType}
              onChange={(e) => {
                setSelectedTransferType(e.target.value);
                setPage(1);
              }}
              className="h-11 rounded-xl border border-ui-border bg-ui-canvas px-3 text-xs font-semibold text-ui-text-primary outline-none focus:border-ui-focus capitalize"
            >
              <option value="">All Types</option>
              <option value="donation">Donation</option>
              <option value="exchange">Exchange</option>
              <option value="sale">Sale Enquiry</option>
            </select>

            <select
              value={selectedCondition}
              onChange={(e) => {
                setSelectedCondition(e.target.value);
                setPage(1);
              }}
              className="h-11 rounded-xl border border-ui-border bg-ui-canvas px-3 text-xs font-semibold text-ui-text-primary outline-none focus:border-ui-focus"
            >
              <option value="">Any Condition</option>
              <option value="New">New</option>
              <option value="Like new">Like new</option>
              <option value="Good">Good</option>
              <option value="Used">Used</option>
            </select>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-ui-text-muted px-1">
          <span>{total} active resources available</span>
          {(search || selectedCategory || selectedCondition || selectedTransferType) && (
            <button
              onClick={() => {
                setSearch('');
                setSelectedCategory('');
                setSelectedCondition('');
                setSelectedTransferType('');
                setPage(1);
              }}
              className="text-blue-600 dark:text-blue-400 font-semibold hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>
      </section>

      {/* Resource Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-24 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mr-3 text-blue-600" />
          <span className="text-sm font-medium">Loading marketplace resources...</span>
        </div>
      ) : resources.length === 0 ? (
        <div className="p-16 text-center bg-ui-surface rounded-2xl border border-ui-border">
          <ShoppingBag className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800 dark:text-white">No Resources Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Try adjusting your search keywords or clearing active filters to find items.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {resources.map((item) => (
            <article
              key={item.id}
              onClick={() => openDetailModal(item)}
              className="group cursor-pointer rounded-2xl border border-ui-border bg-ui-surface overflow-hidden shadow-sm hover:shadow-md hover:border-blue-500/40 transition-all flex flex-col justify-between"
            >
              <div>
                {/* Image or Category placeholder */}
                <div className="relative h-44 bg-slate-100 dark:bg-slate-800/80 overflow-hidden flex items-center justify-center">
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="text-center p-4">
                      <Package className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-1 group-hover:scale-110 transition-transform" />
                      <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
                        {item.category}
                      </span>
                    </div>
                  )}

                  <div className="absolute top-3 left-3 flex gap-1.5">
                    <span
                      className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider shadow-sm ${
                        typePills[item.transfer_type] || 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {item.transfer_type}
                    </span>
                  </div>

                  <div className="absolute bottom-3 right-3">
                    <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-slate-900/70 text-white backdrop-blur-sm">
                      {item.condition}
                    </span>
                  </div>
                </div>

                <div className="p-4 space-y-2">
                  <div className="flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 font-semibold">
                    <Building2 size={13} />
                    <span className="truncate">{item.college?.name}</span>
                  </div>

                  <h3 className="font-bold text-slate-900 dark:text-white text-base leading-snug group-hover:text-blue-600 transition-colors line-clamp-1">
                    {item.name}
                  </h3>

                  <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                    {item.description || 'No description provided.'}
                  </p>
                </div>
              </div>

              <div className="p-4 pt-3 border-t border-ui-border/60 flex items-center justify-between text-xs">
                <div>
                  <span className="text-slate-400 block text-[10px]">Available</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">
                    {item.quantity_available} {item.unit}
                  </span>
                </div>

                {item.transfer_type === 'sale' && item.indicative_price != null && (
                  <div className="text-right">
                    <span className="text-slate-400 block text-[10px]">Price</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">
                      ${Number(item.indicative_price).toFixed(2)}
                    </span>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Resource Detail & Request Modal */}
      {selectedResource && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200 overflow-y-auto"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setSelectedResource(null);
          }}
        >
          <div className="relative w-full max-w-xl my-8 p-6 bg-ui-surface rounded-2xl shadow-2xl border border-ui-border">
            <button
              onClick={() => setSelectedResource(null)}
              className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-ui-subtle"
            >
              <X size={20} />
            </button>

            {submitSuccess ? (
              <div className="text-center py-6">
                <div className="w-16 h-16 mx-auto mb-4 bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 rounded-full flex items-center justify-center">
                  <CheckCircle2 size={36} />
                </div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">Request Submitted Successfully</h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 max-w-sm mx-auto mt-2 leading-relaxed">
                  Your request has been saved to the database. The resource owner at {selectedResource.college?.name} has
                  been notified and will review your request.
                </p>
                <div className="mt-6 flex justify-center gap-3">
                  <button
                    onClick={() => {
                      setSelectedResource(null);
                      onNavigate('My Requests');
                    }}
                    className="py-2.5 px-5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-md"
                  >
                    View Sent Requests
                  </button>
                  <button
                    onClick={() => setSelectedResource(null)}
                    className="py-2.5 px-4 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-semibold"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider mb-2 ${
                        typePills[selectedResource.transfer_type]
                      }`}
                    >
                      {selectedResource.transfer_type}
                    </span>
                    <h2 className="font-display text-2xl font-bold text-slate-900 dark:text-white">
                      {selectedResource.name}
                    </h2>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 bg-ui-subtle rounded-xl text-xs mb-4">
                  <div>
                    <span className="text-slate-400 block text-[10px]">Institution</span>
                    <span className="font-semibold">{selectedResource.college?.name}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Condition</span>
                    <span className="font-semibold">{selectedResource.condition}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Available</span>
                    <span className="font-semibold">
                      {selectedResource.quantity_available} {selectedResource.unit}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">City</span>
                    <span className="font-semibold">{selectedResource.college?.city}</span>
                  </div>
                </div>

                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed mb-5">
                  {selectedResource.description || 'No detailed description provided.'}
                </p>

                {modalError && (
                  <div className="mb-4 p-3 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl text-xs text-rose-600 dark:text-rose-400 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{modalError}</span>
                  </div>
                )}

                <form onSubmit={handleRequestSubmit} className="space-y-4 pt-3 border-t border-ui-border">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Requested Quantity * (Max: {selectedResource.quantity_available})
                      </label>
                      <input
                        type="number"
                        min="1"
                        max={selectedResource.quantity_available}
                        required
                        value={requestedQty}
                        onChange={(e) => setRequestedQty(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                      />
                    </div>

                    {selectedResource.transfer_type === 'exchange' && (
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                          Offered Quantity *
                        </label>
                        <input
                          type="number"
                          min="1"
                          required
                          value={offeredQty}
                          onChange={(e) => setOfferedQty(e.target.value)}
                          className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                        />
                      </div>
                    )}
                  </div>

                  {selectedResource.transfer_type === 'exchange' && (
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Select Resource to Offer in Exchange *
                      </label>
                      {myInventory.length === 0 ? (
                        <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 p-2.5 rounded-lg border border-amber-200">
                          Your institution currently has no active inventory available to propose an exchange. You must create and publish an available listing first.
                        </p>
                      ) : (
                        <select
                          required
                          value={offeredResourceId}
                          onChange={(e) => setOfferedResourceId(e.target.value)}
                          className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                        >
                          <option value="">Choose an available resource from your stock</option>
                          {myInventory.map((item) => (
                            <option key={item.id} value={item.id}>
                              {item.name} ({item.quantity_available} {item.unit} available)
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Academic Purpose / Justification *
                    </label>
                    <textarea
                      required
                      rows="2"
                      value={purpose}
                      onChange={(e) => setPurpose(e.target.value)}
                      placeholder="Explain how this equipment or material will be utilized in your curriculum or lab..."
                      className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Additional Message for Owner (Optional)
                    </label>
                    <input
                      type="text"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      placeholder="e.g. Inquiries regarding delivery timing or specifications..."
                      className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                    />
                  </div>

                  <div className="pt-2 flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setSelectedResource(null)}
                      className="py-2.5 px-4 border border-slate-300 dark:border-slate-600 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="py-2.5 px-5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-md flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Submitting...</span>
                        </>
                      ) : (
                        <>
                          <Send size={14} />
                          <span>Transmit Request</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MarketplaceView;
