import React, { useEffect, useMemo, useState } from 'react';
import {
  Bell,
  BookOpen,
  Building2,
  ChartNoAxesCombined,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  Clock3,
  Command,
  Computer,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Package,
  Scale,
  Search,
  Settings,
  ShieldCheck,
  ShoppingBag,
  Sun,
  Truck,
  X,
  LogIn,
} from 'lucide-react';

import { useAuth } from './context/AuthContext';
import { DashboardView } from './pages/DashboardView';
import { MarketplaceView } from './pages/MarketplaceView';
import { MyListingsView } from './pages/MyListingsView';
import { MyRequestsView } from './pages/MyRequestsView';
import { InventoryView } from './pages/InventoryView';
import { TransfersView } from './pages/TransfersView';
import { CollegeVerificationView } from './components/admin/CollegeVerificationView';
import { DisputeManagementView } from './components/admin/DisputeManagementView';
import { CollegeSettingsView } from './components/settings/CollegeSettingsView';
import { LoginModal } from './components/auth/LoginModal';
import { RegisterModal } from './components/auth/RegisterModal';
import { NotificationToast } from './components/common/NotificationToast';

export function App() {
  const { user, college, isAuthenticated, isPlatformAdmin, isCollegeRep, logout } = useAuth();

  const [activePage, setActivePage] = useState('Overview');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  // Auth Modals State
  const [loginOpen, setLoginOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);

  // Toast Notification State
  const [toast, setToast] = useState(null);

  // Dark mode state
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window === 'undefined') return false;
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  const navigateTo = (page) => {
    setActivePage(page);
    setMobileMenuOpen(false);
    setProfileOpen(false);
    setNotificationsOpen(false);
  };

  const handleSignOut = async () => {
    await logout();
    setToast({
      type: 'info',
      title: 'Signed Out',
      message: 'You have been successfully logged out of CampusCycle.',
    });
    setProfileOpen(false);
    setActivePage('Overview');
  };

  // Dynamic Navigation based on authentication role
  const navigation = useMemo(() => {
    if (isPlatformAdmin) {
      return [
        { label: 'Overview', icon: LayoutDashboard, section: 'WORKSPACE' },
        { label: 'Marketplace', icon: ShoppingBag, section: 'WORKSPACE' },
        { label: 'College Verification', icon: Building2, section: 'ADMINISTRATION' },
        { label: 'Transfer Disputes', icon: Scale, section: 'ADMINISTRATION' },
        { label: 'Transfers', icon: Truck, section: 'MANAGEMENT' },
        { label: 'Analytics', icon: ChartNoAxesCombined, section: 'MANAGEMENT' },
      ];
    }

    return [
      { label: 'Overview', icon: LayoutDashboard, section: 'WORKSPACE' },
      { label: 'Marketplace', icon: ShoppingBag, section: 'WORKSPACE' },
      { label: 'My Listings', icon: Package, section: 'WORKSPACE' },
      { label: 'My Requests', icon: BookOpen, section: 'WORKSPACE' },
      { label: 'Inventory', icon: Computer, section: 'MANAGEMENT' },
      { label: 'Transfers', icon: Truck, section: 'MANAGEMENT' },
      { label: 'Analytics', icon: ChartNoAxesCombined, section: 'MANAGEMENT' },
    ];
  }, [isPlatformAdmin]);

  const userInitials = user?.name
    ? user.name
        .split(' ')
        .map((p) => p[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : 'U';

  return (
    <div className="min-h-screen bg-ui-canvas text-ui-text-primary antialiased">
      {/* Toast Notification Container */}
      {toast && <NotificationToast toast={toast} onClose={() => setToast(null)} />}

      {/* Auth Modals */}
      <LoginModal
        isOpen={loginOpen}
        onClose={() => setLoginOpen(false)}
        onSwitchToRegister={() => setRegisterOpen(true)}
      />
      <RegisterModal
        isOpen={registerOpen}
        onClose={() => setRegisterOpen(false)}
        onSwitchToLogin={() => setLoginOpen(true)}
      />

      <div className="flex min-h-screen">
        {/* Mobile Navigation Backdrop */}
        {mobileMenuOpen && (
          <div
            className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}

        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-ui-border bg-ui-surface transition-transform duration-300 lg:translate-x-0 ${
            mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          {/* Logo Area */}
          <div className="flex h-[76px] items-center justify-between border-b border-ui-border px-6">
            <div
              className="flex items-center gap-3 cursor-pointer"
              onClick={() => navigateTo('Overview')}
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ui-accent text-white shadow-md shadow-blue-500/20">
                <ShieldCheck size={22} />
              </div>
              <div>
                <span className="font-display text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                  CampusCycle
                </span>
                <span className="block text-[10px] font-semibold text-ui-accent tracking-wider uppercase">
                  RESOURCE NETWORK
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setMobileMenuOpen(false)}
              className="rounded-lg p-2 text-ui-text-muted hover:bg-ui-subtle lg:hidden"
            >
              <X size={19} />
            </button>
          </div>

          {/* Navigation Links */}
          <div className="flex-1 overflow-y-auto px-4 py-6">
            <div className="mb-3 px-3 text-[10px] font-bold tracking-[0.14em] text-ui-text-muted">
              CAMPUS WORKSPACE
            </div>

            {navigation.map((item, index) => {
              const Icon = item.icon;
              const previousSection = navigation[index - 1]?.section;
              const showSection = item.section !== previousSection;

              return (
                <div key={item.label}>
                  {showSection && index !== 0 && (
                    <div className="mb-3 mt-7 px-3 text-[10px] font-bold tracking-[0.14em] text-ui-text-muted">
                      {item.section}
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => navigateTo(item.label)}
                    className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-medium transition ${
                      activePage === item.label
                        ? 'bg-ui-accent-soft text-ui-accent font-semibold shadow-sm'
                        : 'text-ui-text-secondary hover:bg-ui-subtle hover:text-ui-text-primary'
                    }`}
                  >
                    <Icon size={18} strokeWidth={1.9} />
                    <span>{item.label}</span>
                  </button>
                </div>
              );
            })}

            <div className="mb-3 mt-8 px-3 text-[10px] font-bold tracking-[0.14em] text-ui-text-muted">
              SUPPORT & SETTINGS
            </div>

            <button
              type="button"
              onClick={() => navigateTo('Settings')}
              className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-medium transition ${
                activePage === 'Settings'
                  ? 'bg-ui-accent-soft text-ui-accent font-semibold'
                  : 'text-ui-text-secondary hover:bg-ui-subtle'
              }`}
            >
              <Settings size={18} />
              <span>{isCollegeRep ? 'College Settings' : 'Settings'}</span>
            </button>

            <button
              type="button"
              onClick={() => navigateTo('Help & Support')}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-medium transition ${
                activePage === 'Help & Support'
                  ? 'bg-ui-accent-soft text-ui-accent font-semibold'
                  : 'text-ui-text-secondary hover:bg-ui-subtle'
              }`}
            >
              <CircleHelp size={18} />
              <span>Help & Support</span>
            </button>
          </div>

          {/* Active Institution Info Footer */}
          <div className="border-t border-ui-border p-4">
            <div className="rounded-xl bg-ui-subtle p-3">
              <div className="flex items-center gap-2">
                {college?.verification_status === 'verified' ? (
                  <ShieldCheck size={16} className="text-emerald-500 shrink-0" />
                ) : college?.verification_status === 'pending' ? (
                  <Clock3 size={16} className="text-amber-500 shrink-0" />
                ) : (
                  <Building2 size={16} className="text-blue-500 shrink-0" />
                )}
                <span className="text-xs font-bold truncate">
                  {isAuthenticated
                    ? isPlatformAdmin
                      ? 'Platform Administration'
                      : college?.name || 'College Workspace'
                    : 'Campus Community'}
                </span>
              </div>
              <p className="mt-1.5 text-[11px] leading-4 text-ui-text-muted">
                {isAuthenticated
                  ? isPlatformAdmin
                    ? 'Global network operator session'
                    : `Status: ${college?.verification_status || 'Active'}`
                  : 'Educational resource sharing & transfer platform.'}
              </p>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <div className="min-h-screen flex-1 lg:pl-64 flex flex-col">
          {/* Topbar */}
          <header className="sticky top-0 z-30 flex h-[76px] items-center justify-between gap-3 border-b border-ui-border bg-ui-surface/95 px-4 backdrop-blur-md sm:px-7 lg:px-9">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(true)}
                className="rounded-lg p-2 text-ui-text-secondary hover:bg-ui-subtle lg:hidden"
              >
                <Menu size={21} />
              </button>

              <div className="relative w-full max-w-[430px]">
                <Search
                  size={17}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ui-text-muted"
                />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      navigateTo('Marketplace');
                    }
                  }}
                  placeholder="Search resources, categories, equipment..."
                  className="h-10 w-full rounded-xl border border-ui-border bg-ui-canvas pl-10 pr-4 text-sm text-ui-text-primary outline-none transition placeholder:text-ui-text-muted focus:border-ui-focus focus:ring-2 focus:ring-ui-focus/15"
                />
                <span className="absolute right-3 top-1/2 hidden -translate-y-1/2 items-center gap-1 rounded border border-ui-border px-1.5 py-0.5 text-[10px] text-ui-text-muted sm:flex">
                  <Command size={10} /> K
                </span>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-1.5 sm:gap-3">
              {/* Theme Toggle */}
              <button
                type="button"
                onClick={() => setDarkMode((val) => !val)}
                className="rounded-xl p-2.5 text-ui-text-secondary transition hover:bg-ui-subtle"
                aria-label="Toggle theme"
              >
                {darkMode ? <Sun size={19} /> : <Moon size={19} />}
              </button>

              {/* Notifications */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setNotificationsOpen((val) => !val);
                    setProfileOpen(false);
                  }}
                  className="relative rounded-xl p-2.5 text-ui-text-secondary transition hover:bg-ui-subtle"
                >
                  <Bell size={19} />
                  <span className="absolute right-2 top-2 h-2 w-2 rounded-full border-2 border-ui-surface bg-ui-accent" />
                </button>

                {notificationsOpen && (
                  <div className="absolute right-0 top-12 z-50 w-[min(320px,calc(100vw-32px))] rounded-2xl border border-ui-border bg-ui-surface p-4 shadow-xl">
                    <div className="flex items-center justify-between pb-2 border-b border-ui-border">
                      <h3 className="font-display font-bold text-sm">System Notifications</h3>
                      <span className="text-[10px] font-semibold text-ui-accent bg-ui-accent-soft px-2 py-0.5 rounded-full">
                        Live
                      </span>
                    </div>
                    <div className="mt-3 space-y-3 text-xs">
                      <div className="flex gap-2.5">
                        <CheckCircle2 size={16} className="text-emerald-500 shrink-0 mt-0.5" />
                        <div>
                          <p className="font-semibold text-slate-800 dark:text-slate-200">Session Active</p>
                          <p className="text-slate-500 text-[11px]">
                            {isAuthenticated ? `Logged in as ${user?.role}` : 'Browsing guest mode.'}
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-2.5">
                        <ShieldCheck size={16} className="text-blue-500 shrink-0 mt-0.5" />
                        <div>
                          <p className="font-semibold text-slate-800 dark:text-slate-200">Platform Security</p>
                          <p className="text-slate-500 text-[11px]">
                            Double-submit CSRF and rotated session cookies active.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Auth Profile / Login Area */}
              {!isAuthenticated ? (
                <div className="flex items-center gap-2 pl-2">
                  <button
                    type="button"
                    onClick={() => setLoginOpen(true)}
                    className="py-2 px-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
                  >
                    <LogIn size={14} />
                    <span>Sign In</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setRegisterOpen(true)}
                    className="hidden sm:inline-flex py-2 px-3.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-semibold transition"
                  >
                    Register
                  </button>
                </div>
              ) : (
                <div className="relative border-l border-ui-border pl-3 sm:pl-4">
                  <button
                    type="button"
                    onClick={() => {
                      setProfileOpen((val) => !val);
                      setNotificationsOpen(false);
                    }}
                    className="flex items-center gap-2 rounded-xl p-1.5 transition hover:bg-ui-subtle"
                  >
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-ui-accent text-xs font-bold text-white shadow-sm">
                      {userInitials}
                    </div>
                    <div className="hidden text-left sm:block">
                      <p className="text-xs font-bold text-slate-900 dark:text-white truncate max-w-[130px]">
                        {user?.name}
                      </p>
                      <p className="text-[10px] text-ui-text-muted capitalize">
                        {user?.role.replace('_', ' ')}
                      </p>
                    </div>
                    <ChevronDown size={14} className="hidden text-ui-text-muted sm:block" />
                  </button>

                  {profileOpen && (
                    <div className="absolute right-0 top-12 z-50 w-56 rounded-2xl border border-ui-border bg-ui-surface p-2 shadow-xl animate-in fade-in duration-150">
                      <div className="px-3 py-2 border-b border-ui-border mb-1">
                        <p className="text-xs font-bold text-slate-900 dark:text-white truncate">{user?.name}</p>
                        <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
                        {college?.name && (
                          <p className="text-[10px] font-semibold text-blue-600 dark:text-blue-400 mt-1 truncate">
                            {college.name}
                          </p>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={() => navigateTo('Settings')}
                        className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium hover:bg-ui-subtle transition"
                      >
                        <Settings size={15} />
                        <span>{isCollegeRep ? 'College Settings' : 'Settings'}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => navigateTo('Help & Support')}
                        className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium hover:bg-ui-subtle transition"
                      >
                        <CircleHelp size={15} />
                        <span>Help & Support</span>
                      </button>

                      <div className="my-1 border-t border-ui-border" />

                      <button
                        type="button"
                        onClick={handleSignOut}
                        className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition"
                      >
                        <LogOut size={15} />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </header>

          {/* Main Application Body */}
          <main className="mx-auto max-w-[1500px] w-full flex-1 px-4 py-7 sm:px-7 lg:px-9 lg:py-8">
            {activePage === 'Overview' ? (
              <DashboardView
                onNavigate={navigateTo}
                onOpenLogin={() => setLoginOpen(true)}
                onOpenRegister={() => setRegisterOpen(true)}
              />
            ) : activePage === 'Marketplace' ? (
              <MarketplaceView
                onNavigate={navigateTo}
                onOpenLogin={() => setLoginOpen(true)}
                onShowToast={setToast}
              />
            ) : activePage === 'My Listings' ? (
              <MyListingsView
                onShowToast={setToast}
                onOpenLogin={() => setLoginOpen(true)}
              />
            ) : activePage === 'My Requests' ? (
              <MyRequestsView
                onShowToast={setToast}
                onNavigate={navigateTo}
              />
            ) : activePage === 'Inventory' ? (
              <InventoryView onNavigate={navigateTo} />
            ) : activePage === 'Transfers' ? (
              <TransfersView
                onShowToast={setToast}
                onNavigate={navigateTo}
              />
            ) : activePage === 'College Verification' && isPlatformAdmin ? (
              <CollegeVerificationView onShowToast={setToast} />
            ) : activePage === 'Transfer Disputes' && isPlatformAdmin ? (
              <DisputeManagementView onShowToast={setToast} />
            ) : activePage === 'Settings' && isCollegeRep ? (
              <CollegeSettingsView onShowToast={setToast} />
            ) : activePage === 'Analytics' ? (
              <Analytics />
            ) : (
              <ModulePlaceholder
                page={activePage}
                onBack={() => navigateTo('Overview')}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

// Preserve existing visual demonstration Analytics component per project rules
function Analytics() {
  const [period, setPeriod] = useState('This month');

  const data = {
    'This week': {
      resources: 18,
      donations: 8,
      exchanges: 6,
      enquiries: 4,
      requests: 12,
      completed: 9,
      trend: [35, 55, 40, 75, 60, 90, 70],
    },
    'This month': {
      resources: 128,
      donations: 54,
      exchanges: 46,
      enquiries: 28,
      requests: 86,
      completed: 72,
      trend: [35, 55, 45, 70, 60, 85, 75, 95, 65, 80, 90, 100],
    },
    'This year': {
      resources: 842,
      donations: 356,
      exchanges: 301,
      enquiries: 185,
      requests: 624,
      completed: 518,
      trend: [30, 45, 40, 60, 55, 75, 65, 90, 80, 100, 85, 95],
    },
  };

  const stats = data[period] || data['This month'];

  const categories = [
    { name: 'Books & study material', count: 42 },
    { name: 'Electronics', count: 28 },
    { name: 'Lab equipment', count: 22 },
    { name: 'Stationery', count: 18 },
    { name: 'Others', count: 18 },
  ];

  const totalCategoryCount = categories.reduce((sum, item) => sum + item.count, 0);

  const metrics = [
    {
      label: 'Total resources',
      value: stats.resources,
      description: 'Resources listed',
      color: 'text-ui-accent',
    },
    {
      label: 'Donations',
      value: stats.donations,
      description: 'Resources shared for free',
      color: 'text-ui-success-text',
    },
    {
      label: 'Exchanges',
      value: stats.exchanges,
      description: 'Successful resource exchanges',
      color: 'text-ui-accent',
    },
    {
      label: 'Purchase enquiries',
      value: stats.enquiries,
      description: 'Enquiries submitted',
      color: 'text-ui-warning-text',
    },
  ];

  return (
    <div className="space-y-7 animate-in fade-in duration-200">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-ui-accent">WORKSPACE / ANALYTICS</p>
          <h1 className="mt-2 font-display text-3xl font-bold">Campus Analytics Overview</h1>
          <p className="mt-2 text-text-secondary">
            Demonstration analytics. Dedicated Phase 10 integration will generate real database reports.
          </p>
        </div>

        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="rounded-xl border border-ui-border bg-ui-surface px-4 py-2.5 text-xs font-semibold"
        >
          <option>This week</option>
          <option>This month</option>
          <option>This year</option>
        </select>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className="rounded-2xl border border-ui-border bg-ui-surface p-5">
            <p className="text-xs font-semibold text-text-secondary">{metric.label}</p>
            <p className={`mt-3 text-3xl font-bold ${metric.color}`}>{metric.value}</p>
            <p className="mt-2 text-xs text-text-muted">{metric.description}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-ui-border bg-ui-surface p-6">
          <h2 className="font-display text-base font-bold">Request Performance</h2>
          <p className="mt-1 text-xs text-text-secondary">Requests submitted and completed</p>

          <div className="mt-6 flex items-end gap-8">
            <div>
              <p className="text-3xl font-bold">{stats.requests}</p>
              <p className="mt-1 text-xs text-text-muted">Total requests</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-ui-success-text">{stats.completed}</p>
              <p className="mt-1 text-xs text-text-muted">Completed</p>
            </div>
          </div>

          <div className="mt-6 h-3 overflow-hidden rounded-full bg-ui-subtle">
            <div
              className="h-full rounded-full bg-ui-success"
              style={{
                width: `${stats.requests > 0 ? (stats.completed / stats.requests) * 100 : 0}%`,
              }}
            />
          </div>

          <p className="mt-2 text-xs text-text-secondary">
            {Math.round((stats.completed / stats.requests) * 100)}% completion rate
          </p>
        </div>

        <div className="rounded-2xl border border-ui-border bg-ui-surface p-6">
          <h2 className="font-display text-base font-bold">Transfer Performance</h2>
          <p className="mt-1 text-xs text-text-secondary">Resource transfers completed</p>

          <p className="mt-6 text-3xl font-bold">{Math.round(stats.completed * 0.8)}</p>
          <p className="mt-1 text-xs text-text-secondary">Estimated completed transfers</p>
        </div>
      </div>

      <div className="rounded-2xl border border-ui-border bg-ui-surface p-6">
        <h2 className="font-display text-base font-bold">Resource Category Distribution</h2>
        <div className="mt-6 space-y-4">
          {categories.map((category) => {
            const percentage = Math.round((category.count / totalCategoryCount) * 100);

            return (
              <div key={category.name}>
                <div className="mb-1.5 flex justify-between gap-3 text-xs">
                  <span className="font-medium">{category.name}</span>
                  <span className="text-text-secondary">
                    {category.count} ({percentage}%)
                  </span>
                </div>

                <div className="h-2 overflow-hidden rounded-full bg-ui-subtle">
                  <div className="h-full rounded-full bg-ui-accent" style={{ width: `${percentage}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ModulePlaceholder({ page, onBack }) {
  return (
    <section className="mx-auto max-w-2xl py-12">
      <div className="rounded-2xl border border-ui-border bg-ui-surface p-8 sm:p-10 text-center">
        <div className="mb-4 mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-ui-accent-soft text-ui-accent">
          <Package size={26} />
        </div>
        <p className="text-xs font-bold tracking-wider text-ui-accent uppercase">CAMPUSCYCLE</p>
        <h2 className="mt-2 font-display text-2xl font-bold">{page}</h2>
        <p className="mt-2 text-xs leading-5 text-ui-text-secondary max-w-sm mx-auto">
          This section is available in the CampusCycle platform. For help, contact campus support or your administrator.
        </p>
        <button
          type="button"
          onClick={onBack}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-ui-accent px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-ui-accent-hover"
        >
          Return to Overview
        </button>
      </div>
    </section>
  );
}

export default App;
