import React, { useEffect, useState, useCallback } from 'react';
import { Computer, Search, Package, ShieldCheck, Loader2 } from 'lucide-react';
import { resourcesApi } from '../api/resources';
import { useAuth } from '../context/AuthContext';

export const InventoryView = ({ onNavigate }) => {
  const { college, isAuthenticated, isVerifiedCollege } = useAuth();
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');

  const fetchInventory = useCallback(async () => {
    if (!isAuthenticated || !isVerifiedCollege) return;
    setIsLoading(true);
    try {
      const res = await resourcesApi.getMyInventory();
      setItems(res?.data?.items || []);
    } catch (err) {
      console.error('Failed to load inventory:', err);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, isVerifiedCollege]);

  useEffect(() => {
    fetchInventory();
  }, [fetchInventory]);

  const totalQuantity = items.reduce((sum, item) => sum + (item.quantity_total || 0), 0);
  const totalReserved = items.reduce((sum, item) => sum + (item.quantity_reserved || 0), 0);
  const totalAvailable = items.reduce((sum, item) => sum + (item.quantity_available || 0), 0);

  const filteredItems = items.filter((item) => {
    const matchesSearch =
      !search.trim() ||
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.category.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === 'All' ||
      (statusFilter === 'Available' && item.quantity_available > 0) ||
      (statusFilter === 'Fully Reserved' && item.quantity_available === 0 && item.quantity_reserved > 0) ||
      (statusFilter === 'Depleted' && item.status === 'depleted');

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-7 animate-in fade-in duration-200">
      {/* Header */}
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-ui-text-muted">
            <span>WORKSPACE</span>
            <span>/</span>
            <span className="text-ui-accent">INVENTORY</span>
          </div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-[34px]">
            Institutional Inventory
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-ui-text-secondary">
            Live stock, active reservations, and available units for {college?.name || 'your institution'}.
            Reservations are managed atomically through request and transfer workflows.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onNavigate('My Listings')}
          className="py-2.5 px-4 bg-ui-accent hover:bg-ui-accent-hover text-white rounded-xl text-xs font-semibold shadow-md transition"
        >
          Manage Listings
        </button>
      </section>

      {/* Statistics Cards */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Resource Types', value: items.length, icon: Package, color: 'blue' },
          { label: 'Total Stock Quantity', value: totalQuantity, icon: Computer, color: 'indigo' },
          { label: 'Available for Request', value: totalAvailable, icon: ShieldCheck, color: 'emerald' },
          { label: 'Reserved for Transfers', value: totalReserved, icon: Computer, color: 'amber' },
        ].map((card) => {
          const Icon = card.icon;
          const colors = {
            blue: 'bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400',
            indigo: 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400',
            emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400',
            amber: 'bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400',
          };

          return (
            <article key={card.label} className="rounded-2xl border border-ui-border bg-ui-surface p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-ui-text-secondary">{card.label}</p>
                <div className={`p-2.5 rounded-xl ${colors[card.color]}`}>
                  <Icon size={19} />
                </div>
              </div>
              <p className="mt-3 font-display text-3xl font-bold text-slate-900 dark:text-white">
                {isLoading ? <Loader2 className="w-6 h-6 animate-spin text-slate-400" /> : card.value}
              </p>
            </article>
          );
        })}
      </section>

      {/* Filter and Search Bar */}
      <section className="rounded-2xl border border-ui-border bg-ui-surface p-4 shadow-sm flex flex-col sm:flex-row gap-3 justify-between items-stretch sm:items-center">
        <div className="flex items-center gap-2">
          {['All', 'Available', 'Fully Reserved', 'Depleted'].map((tab) => (
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
            placeholder="Search inventory..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full sm:w-64 pl-9 pr-3 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </section>

      {/* Inventory Table */}
      <section className="overflow-hidden rounded-2xl border border-ui-border bg-ui-surface shadow-sm">
        <div className="border-b border-ui-border px-5 py-4 flex items-center justify-between">
          <h2 className="font-display text-base font-bold text-slate-900 dark:text-white">Active Stock Register</h2>
          <span className="text-xs text-slate-500">{filteredItems.length} records</span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin mr-3 text-blue-600" />
            <span className="text-sm font-medium">Loading inventory data...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No inventory resources found matching your search.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[750px] text-left text-sm">
              <thead className="bg-ui-subtle text-slate-500 text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="p-4">Resource</th>
                  <th className="p-4">Category</th>
                  <th className="p-4">Condition</th>
                  <th className="p-4">Total Stock</th>
                  <th className="p-4">Reserved</th>
                  <th className="p-4">Available</th>
                  <th className="p-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ui-border">
                {filteredItems.map((item) => (
                  <tr key={item.id} className="hover:bg-ui-subtle/50 transition-colors">
                    <td className="p-4 font-semibold text-slate-900 dark:text-white">{item.name}</td>
                    <td className="p-4 text-xs text-slate-600 dark:text-slate-300">{item.category}</td>
                    <td className="p-4 text-xs text-slate-600 dark:text-slate-300">{item.condition}</td>
                    <td className="p-4 text-slate-700 dark:text-slate-300">
                      {item.quantity_total} <span className="text-xs text-slate-400">{item.unit}</span>
                    </td>
                    <td className="p-4 font-semibold text-amber-600 dark:text-amber-400">
                      {item.quantity_reserved}
                    </td>
                    <td className="p-4 font-bold text-emerald-600 dark:text-emerald-400">
                      {item.quantity_available}
                    </td>
                    <td className="p-4 text-right">
                      <span
                        className={`inline-block px-2.5 py-1 rounded-full text-xs font-bold capitalize ${
                          item.quantity_available > 0
                            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                            : item.quantity_reserved > 0
                            ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
                            : 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300'
                        }`}
                      >
                        {item.quantity_available > 0
                          ? 'Available'
                          : item.quantity_reserved > 0
                          ? 'Reserved'
                          : 'Depleted'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default InventoryView;
