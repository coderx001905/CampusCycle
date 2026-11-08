import React, { useEffect, useState, useCallback } from 'react';
import {
  Package,
  Plus,
  Search,
  CheckCircle2,
  Clock3,
  XCircle,
  Pencil,
  X,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { resourcesApi } from '../api/resources';

export const MyListingsView = ({ onShowToast, onOpenLogin }) => {
  const { college, isAuthenticated, isVerifiedCollege } = useAuth();
  const [listings, setListings] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('All');
  const [search, setSearch] = useState('');

  // Create / Edit modal state
  const [showModal, setShowModal] = useState(false);
  const [editingResource, setEditingResource] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    category: 'Books',
    condition: 'Good',
    quantity: 1,
    unit: 'units',
    transfer_type: 'donation',
    indicative_price: '',
    description: '',
  });
  const [imageFile, setImageFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  const fetchMyListings = useCallback(async () => {
    if (!college?.id) return;
    setIsLoading(true);
    try {
      // 1. Fetch full owned inventory (includes active, inactive, and depleted items)
      let inventoryItems = [];
      try {
        const invRes = await resourcesApi.getMyInventory();
        inventoryItems = invRes?.data?.items || [];
      } catch (invErr) {
        console.warn('Inventory fetch failed (e.g. unverified college):', invErr);
      }

      // 2. Fetch marketplace listings for active metadata (transfer_type, description, image_url)
      const mktRes = await resourcesApi.listResources({
        college_id: college.id,
        page_size: 100,
      });
      const marketplaceItems = mktRes?.data?.items || [];
      const marketplaceMap = new Map(marketplaceItems.map((item) => [item.id, item]));

      if (inventoryItems.length > 0) {
        const merged = inventoryItems.map((inv) => {
          const mkt = marketplaceMap.get(inv.id);
          return {
            ...inv,
            transfer_type: mkt?.transfer_type || inv.transfer_type || 'donation',
            description: mkt?.description || '',
            indicative_price: mkt?.indicative_price != null ? mkt.indicative_price : null,
            image_url: mkt?.image_url || null,
          };
        });
        setListings(merged);
      } else {
        setListings(marketplaceItems);
      }
    } catch (err) {
      console.error('Error fetching owned listings:', err);
    } finally {
      setIsLoading(false);
    }
  }, [college]);

  useEffect(() => {
    fetchMyListings();
  }, [fetchMyListings]);

  const openCreateModal = () => {
    if (!isAuthenticated) {
      onOpenLogin();
      return;
    }
    if (!isVerifiedCollege) {
      onShowToast?.({
        type: 'error',
        title: 'Action Restricted',
        message: 'Your college must be verified before listing resources.',
      });
      return;
    }
    setEditingResource(null);
    setFormData({
      name: '',
      category: 'Books',
      condition: 'Good',
      quantity: 1,
      unit: 'units',
      transfer_type: 'donation',
      indicative_price: '',
      description: '',
    });
    setImageFile(null);
    setFormError('');
    setShowModal(true);
  };

  const openEditModal = async (resource) => {
    setEditingResource(resource);
    let fullResource = resource;
    try {
      const details = await resourcesApi.getResource(resource.id);
      if (details?.data) fullResource = details.data;
    } catch {
      // fallback to existing resource properties
    }
    setFormData({
      name: fullResource.name,
      category: fullResource.category,
      condition: fullResource.condition,
      unit: fullResource.unit,
      transfer_type: fullResource.transfer_type || 'donation',
      indicative_price: fullResource.indicative_price != null ? String(fullResource.indicative_price) : '',
      description: fullResource.description || '',
    });
    setImageFile(null);
    setFormError('');
    setShowModal(true);
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!formData.name.trim()) {
      setFormError('Resource name is required.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingResource) {
        // ResourceUpdate schema (does NOT support quantity changes to preserve inventory integrity)
        const updatePayload = {
          name: formData.name.trim(),
          category: formData.category,
          condition: formData.condition,
          unit: formData.unit.trim(),
          transfer_type: formData.transfer_type,
          description: formData.description.trim() || null,
          indicative_price:
            formData.transfer_type === 'sale' && formData.indicative_price
              ? Number(formData.indicative_price)
              : null,
        };

        await resourcesApi.updateResource(editingResource.id, updatePayload);

        // Upload image if newly selected
        if (imageFile) {
          await resourcesApi.uploadImage(editingResource.id, imageFile);
        }

        onShowToast?.({
          type: 'success',
          title: 'Listing Updated',
          message: `"${formData.name}" has been updated.`,
        });
      } else {
        // ResourceCreate schema
        const createPayload = {
          name: formData.name.trim(),
          category: formData.category,
          condition: formData.condition,
          quantity: Number(formData.quantity) || 1,
          unit: formData.unit.trim() || 'units',
          transfer_type: formData.transfer_type,
          description: formData.description.trim() || null,
          indicative_price:
            formData.transfer_type === 'sale' && formData.indicative_price
              ? Number(formData.indicative_price)
              : null,
        };

        const res = await resourcesApi.createResource(createPayload);
        const createdId = res?.data?.id;

        // Upload image if selected
        if (imageFile && createdId) {
          try {
            await resourcesApi.uploadImage(createdId, imageFile);
          } catch (imgErr) {
            console.warn('Image upload failed after creation:', imgErr);
          }
        }

        onShowToast?.({
          type: 'success',
          title: 'Resource Listed',
          message: `"${formData.name}" is now published on the marketplace.`,
        });
      }

      setShowModal(false);
      await fetchMyListings();
    } catch (err) {
      setFormError(
        err.response?.data?.error?.message ||
        err.response?.data?.detail ||
        'Failed to save resource listing.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (resource) => {
    const nextStatus = resource.status === 'active' ? 'inactive' : 'active';
    try {
      await resourcesApi.updateResourceStatus(resource.id, nextStatus);
      onShowToast?.({
        type: 'success',
        title: 'Status Updated',
        message: `Listing is now marked as ${nextStatus}.`,
      });
      await fetchMyListings();
    } catch (err) {
      onShowToast?.({
        type: 'error',
        title: 'Status Update Failed',
        message: err.response?.data?.detail || 'Could not change listing status.',
      });
    }
  };

  const filteredListings = listings.filter((item) => {
    const matchesStatus =
      statusFilter === 'All' ||
      (statusFilter === 'Active' && item.status === 'active') ||
      (statusFilter === 'Inactive' && item.status === 'inactive') ||
      (statusFilter === 'Depleted' && item.status === 'depleted');

    const matchesSearch =
      !search.trim() ||
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.category.toLowerCase().includes(search.toLowerCase());

    return matchesStatus && matchesSearch;
  });

  const activeCount = listings.filter((l) => l.status === 'active').length;
  const inactiveCount = listings.filter((l) => l.status === 'inactive').length;
  const depletedCount = listings.filter((l) => l.status === 'depleted').length;

  return (
    <div className="space-y-7 animate-in fade-in duration-200">
      {/* Header */}
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-ui-text-muted">
            <span>WORKSPACE</span>
            <span>/</span>
            <span className="text-ui-accent">MY LISTINGS</span>
          </div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-[34px]">
            Institutional Listings
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-ui-text-secondary">
            Manage resources published by {college?.name || 'your institution'}. Track stock and status.
          </p>
        </div>

        <button
          type="button"
          onClick={openCreateModal}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-ui-accent px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:bg-ui-accent-hover"
        >
          <Plus size={17} />
          Create New Listing
        </button>
      </section>

      {/* Summary Cards */}
      <section className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Active Listings', value: activeCount, icon: CheckCircle2, color: 'emerald' },
          { label: 'Inactive / Hidden', value: inactiveCount, icon: Clock3, color: 'amber' },
          { label: 'Depleted Stock', value: depletedCount, icon: XCircle, color: 'rose' },
        ].map((card) => {
          const Icon = card.icon;
          const colors = {
            emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400',
            amber: 'bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400',
            rose: 'bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400',
          };

          return (
            <article key={card.label} className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-ui-text-secondary">{card.label}</p>
                <div className={`p-2.5 rounded-xl ${colors[card.color]}`}>
                  <Icon size={19} />
                </div>
              </div>
              <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">{card.value}</p>
            </article>
          );
        })}
      </section>

      {/* Search & Filter Bar */}
      <section className="rounded-2xl border border-ui-border bg-ui-surface p-4 shadow-sm flex flex-col sm:flex-row gap-3 justify-between items-stretch sm:items-center">
        <div className="flex items-center gap-2">
          {['All', 'Active', 'Inactive', 'Depleted'].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                statusFilter === tab
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search your listings..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full sm:w-64 pl-9 pr-3 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </section>

      {/* Listings Table */}
      <section className="overflow-hidden rounded-2xl border border-ui-border bg-ui-surface shadow-sm">
        <div className="border-b border-ui-border px-5 py-4 flex items-center justify-between">
          <h2 className="font-display text-base font-bold text-slate-900 dark:text-white">Published Resources</h2>
          <span className="text-xs text-slate-500">{filteredListings.length} displayed</span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin mr-3 text-blue-600" />
            <span className="text-sm font-medium">Loading listings...</span>
          </div>
        ) : filteredListings.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No listings found matching your current filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[750px] text-left text-sm">
              <thead className="bg-ui-subtle text-slate-500 text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="p-4">Resource</th>
                  <th className="p-4">Category</th>
                  <th className="p-4">Type</th>
                  <th className="p-4">Available Qty</th>
                  <th className="p-4">Condition</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ui-border">
                {filteredListings.map((item) => (
                  <tr key={item.id} className="hover:bg-ui-subtle/50 transition-colors">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 overflow-hidden flex items-center justify-center shrink-0">
                          {item.image_url ? (
                            <img src={item.image_url} alt="" className="w-full h-full object-cover" />
                          ) : (
                            <Package className="w-5 h-5 text-slate-400" />
                          )}
                        </div>
                        <div>
                          <h4 className="font-semibold text-slate-900 dark:text-white">{item.name}</h4>
                          <p className="text-xs text-slate-400 truncate max-w-xs">{item.description}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4 text-xs text-slate-600 dark:text-slate-300">{item.category}</td>
                    <td className="p-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                        {item.transfer_type}
                      </span>
                    </td>
                    <td className="p-4 font-bold text-slate-900 dark:text-white">
                      {item.quantity_available} <span className="font-normal text-xs text-slate-400">{item.unit}</span>
                    </td>
                    <td className="p-4 text-xs text-slate-600 dark:text-slate-300">{item.condition}</td>
                    <td className="p-4">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[11px] font-bold capitalize ${
                          item.status === 'active'
                            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                            : item.status === 'inactive'
                            ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
                            : 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300'
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(item)}
                          className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/40 rounded-lg transition-colors"
                          title="Edit details"
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          onClick={() => handleToggleStatus(item)}
                          className={`text-xs font-semibold px-2.5 py-1 rounded-lg transition-colors ${
                            item.status === 'active'
                              ? 'text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/30'
                              : 'text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30'
                          }`}
                        >
                          {item.status === 'active' ? 'Hide' : 'Publish'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200 overflow-y-auto">
          <div className="relative w-full max-w-xl my-8 p-6 bg-ui-surface rounded-2xl shadow-2xl border border-ui-border">
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-ui-subtle"
            >
              <X size={20} />
            </button>

            <h3 className="text-xl font-bold font-display text-slate-900 dark:text-white mb-1">
              {editingResource ? 'Edit Resource Details' : 'Create New Resource Listing'}
            </h3>
            <p className="text-xs text-slate-500 mb-5">
              {editingResource
                ? 'Update listing description, category or condition. (Inventory quantity remains protected).'
                : 'Publish an educational resource to the campus network with initial stock.'}
            </p>

            {formError && (
              <div className="mb-4 p-3 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl text-xs text-rose-600 dark:text-rose-400 flex items-center gap-2">
                <AlertCircle size={15} />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleFormSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Resource Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Oscilloscope Model 2200, Organic Chemistry Textbook"
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Category *
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                  >
                    <option value="Books">Books</option>
                    <option value="Electronics">Electronics</option>
                    <option value="Lab equipment">Lab equipment</option>
                    <option value="Study material">Study material</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Condition *
                  </label>
                  <select
                    value={formData.condition}
                    onChange={(e) => setFormData({ ...formData, condition: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                  >
                    <option value="New">New</option>
                    <option value="Like new">Like new</option>
                    <option value="Good">Good</option>
                    <option value="Used">Used</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Listing Transfer Type *
                  </label>
                  <select
                    value={formData.transfer_type}
                    onChange={(e) => setFormData({ ...formData, transfer_type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white capitalize"
                  >
                    <option value="donation">Donation</option>
                    <option value="exchange">Exchange</option>
                    <option value="sale">Sale Enquiry</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Unit Type *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                    placeholder="units, boxes, kits, copies"
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                  />
                </div>
              </div>

              {!editingResource && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Initial Stock Quantity *
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                  />
                </div>
              )}

              {formData.transfer_type === 'sale' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Indicative Price ($) (Optional)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.indicative_price}
                    onChange={(e) => setFormData({ ...formData, indicative_price: e.target.value })}
                    placeholder="0.00"
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  rows="3"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Provide specifications, model, edition or condition notes..."
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Resource Photo (JPEG, PNG, WebP • Max 2MB)
                </label>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="py-2.5 px-4 border border-slate-300 dark:border-slate-600 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="py-2.5 px-5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-md flex items-center gap-1.5 disabled:opacity-50"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  <span>{editingResource ? 'Save Changes' : 'Publish Resource'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default MyListingsView;
