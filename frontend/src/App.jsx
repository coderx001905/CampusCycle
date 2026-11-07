
import { useEffect, useMemo, useState } from "react";
import {
  Pencil,
  Trash2,
  Save,
  MapPin,
  Send,
  SlidersHorizontal,
  UserRound,
  Activity,
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Bell,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  Clock3,
  Command,
  Computer,
  Handshake,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Plus,
  Recycle,
  Search,
  Settings,
  ShieldCheck,
  ShoppingBag,
  Sun,
  Moon,
  Truck,
  Users,
  X,
  ChartNoAxesCombined,
} from "lucide-react";

 const typeStyles = {
    Donation: "bg-ui-success-bg text-ui-success-text",
    Exchange: "bg-ui-accent-soft text-ui-accent",
    "Purchase enquiry": "bg-ui-warning-bg text-ui-warning-text",
  };
const navigation = [
  { label: "Overview", icon: LayoutDashboard, section: "WORKSPACE" },
  { label: "Marketplace", icon: ShoppingBag, section: "WORKSPACE" },
  { label: "My Listings", icon: Package, section: "WORKSPACE" },
  { label: "My Requests", icon: BookOpen, section: "WORKSPACE" },
  { label: "Inventory", icon: Computer, section: "MANAGEMENT" },
  { label: "Transfers", icon: Truck, section: "MANAGEMENT" },
  { label: "Analytics", icon: ChartNoAxesCombined, section: "MANAGEMENT" },
];

const listings = [
  {
    id: 1,
    name: "Engineering Mathematics",
    category: "Books",
    owner: "Rahul Sharma",
    type: "Donation",
    status: "Available",
    icon: BookOpen,
    initials: "RS",
    color: "blue",
    time: "12 min ago",
  },
  {
    id: 2,
    name: "Dell Laptop Stand",
    category: "Electronics",
    owner: "Ananya R",
    type: "Exchange",
    status: "Available",
    icon: Computer,
    initials: "AR",
    color: "green",
    time: "35 min ago",
  },
  {
    id: 3,
    name: "Chemistry Lab Kit",
    category: "Lab equipment",
    owner: "Arjun K",
    type: "Purchase enquiry",
    status: "Reserved",
    icon: Package,
    initials: "AK",
    color: "amber",
    time: "1 hour ago",
  },
  {
    id: 4,
    name: "Data Structures Notes",
    category: "Study material",
    owner: "Meera S",
    type: "Donation",
    status: "Available",
    icon: BookOpen,
    initials: "MS",
    color: "blue",
    time: "2 hours ago",
  },
];

const activities = [
  {
    title: "New resource listed",
    detail: "Engineering Mathematics · Rahul Sharma",
    time: "12 min ago",
    icon: Package,
    color: "blue",
  },
  {
    title: "Request submitted",
    detail: "Laptop Stand · Ananya R",
    time: "38 min ago",
    icon: ArrowDownLeft,
    color: "green",
  },
  {
    title: "Transfer completed",
    detail: "Physics Lab Kit · Science Department",
    time: "2 hours ago",
    icon: Truck,
    color: "amber",
  },
];

function App() {
  const [darkMode, setDarkMode] = useState(
    () => localStorage.getItem("campuscycle-theme") === "dark"
  );
  const [activePage, setActivePage] = useState("Overview");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("campuscycle-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const filteredListings = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    if (!query) return listings;

    return listings.filter((item) =>
      [item.name, item.category, item.owner, item.type]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [searchQuery]);

  function navigateTo(page) {
    setActivePage(page);
    setMobileMenuOpen(false);
    setNotificationsOpen(false);
    setProfileOpen(false);
  }

  return (
    <div className="min-h-screen bg-ui-canvas text-ui-text-primary">
      <div className="min-h-screen">
        {mobileMenuOpen && (
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          />
        )}

        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-ui-border bg-ui-surface transition-transform duration-200 lg:translate-x-0 ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
            }`}
        >
          <div className="flex h-[76px] items-center justify-between border-b border-ui-border px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ui-accent text-white">
                <Recycle size={23} strokeWidth={2.3} />
              </div>
              <div>
                <h1 className="font-display text-lg font-bold tracking-tight">
                  CampusCycle
                </h1>
                <p className="text-[11px] text-ui-text-muted">
                  Campus resource sharing
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setMobileMenuOpen(false)}
              className="rounded-lg p-2 text-ui-text-muted hover:bg-ui-subtle lg:hidden"
              aria-label="Close sidebar"
            >
              <X size={19} />
            </button>
          </div>

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
                    className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-medium transition ${activePage === item.label
                      ? "bg-ui-accent-soft text-ui-accent"
                      : "text-ui-text-secondary hover:bg-ui-subtle hover:text-ui-text-primary"
                      }`}
                  >
                    <Icon size={18} strokeWidth={1.9} />
                    <span>{item.label}</span>

                    {item.label === "My Requests" && (
                      <span className="ml-auto rounded-full bg-ui-warning-bg px-2 py-0.5 text-[10px] font-bold text-ui-warning-text">
                        4
                      </span>
                    )}
                  </button>
                </div>
              );
            })}

            <div className="mb-3 mt-8 px-3 text-[10px] font-bold tracking-[0.14em] text-ui-text-muted">
              SUPPORT
            </div>

            <button
              type="button"
              onClick={() => navigateTo("Help & Support")}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-medium text-ui-text-secondary transition hover:bg-ui-subtle"
            >
              <CircleHelp size={18} />
              Help & Support
            </button>

            <button
              type="button"
              onClick={() => navigateTo("Settings")}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-medium text-ui-text-secondary transition hover:bg-ui-subtle"
            >
              <Settings size={18} />
              Settings
            </button>
          </div>

          {/* Campus information */}
          <div className="border-t border-ui-border p-4">
            <div className="rounded-xl bg-ui-subtle p-3">
              <div className="flex items-center gap-2">
                <ShieldCheck size={17} className="text-ui-success" />
                <span className="text-xs font-semibold">
                  Campus community
                </span>
              </div>
              <p className="mt-2 text-[11px] leading-5 text-ui-text-muted">
                Sharing resources. Reducing waste. Building a better campus.
              </p>
            </div>
          </div>
        </aside>

        {/* Main application */}
        <div className="min-h-screen lg:pl-64">
          {/* Topbar */}
          <header className="sticky top-0 z-30 flex h-[76px] items-center justify-between gap-3 border-b border-ui-border bg-ui-surface/95 px-4 backdrop-blur-md sm:px-7 lg:px-9">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(true)}
                className="rounded-lg p-2 text-ui-text-secondary hover:bg-ui-subtle lg:hidden"
                aria-label="Open navigation"
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
                  onChange={(event) => {
                    setSearchQuery(event.target.value);
                    setActivePage("Overview");
                  }}
                  placeholder="Search resources, categories..."
                  className="h-10 w-full rounded-xl border border-ui-border bg-ui-canvas pl-10 pr-4 text-sm text-ui-text-primary outline-none transition placeholder:text-ui-text-muted focus:border-ui-focus focus:ring-2 focus:ring-ui-focus/15"
                />
                <span className="absolute right-3 top-1/2 hidden -translate-y-1/2 items-center gap-1 rounded border border-ui-border px-1.5 py-0.5 text-[10px] text-ui-text-muted sm:flex">
                  <Command size={10} /> K
                </span>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-1 sm:gap-3">
              <button
                type="button"
                onClick={() => setDarkMode((value) => !value)}
                className="rounded-xl p-2.5 text-ui-text-secondary transition hover:bg-ui-subtle"
                aria-label="Toggle theme"
                title="Toggle theme"
              >
                {darkMode ? <Sun size={19} /> : <Moon size={19} />}
              </button>

              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setNotificationsOpen((value) => !value);
                    setProfileOpen(false);
                  }}
                  className="relative rounded-xl p-2.5 text-ui-text-secondary transition hover:bg-ui-subtle"
                  aria-label="Notifications"
                >
                  <Bell size={19} />
                  <span className="absolute right-2 top-2 h-2 w-2 rounded-full border-2 border-ui-surface bg-ui-danger" />
                </button>

                {notificationsOpen && (
                  <div className="absolute right-0 top-12 z-50 w-[min(320px,calc(100vw-32px))] rounded-2xl border border-ui-border bg-ui-surface p-4 shadow-xl">
                    <div className="flex items-center justify-between">
                      <h3 className="font-display font-bold">Notifications</h3>
                      <span className="rounded-full bg-ui-accent-soft px-2 py-1 text-[10px] font-semibold text-ui-accent">
                        2 new
                      </span>
                    </div>
                    <div className="mt-4 space-y-4">
                      <div className="flex gap-3">
                        <div className="rounded-lg bg-ui-success-bg p-2 text-ui-success">
                          <CheckCircle2 size={17} />
                        </div>
                        <div>
                          <p className="text-sm font-semibold">Request update</p>
                          <p className="mt-1 text-xs text-ui-text-muted">
                            Your sample request has been updated.
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <div className="rounded-lg bg-ui-warning-bg p-2 text-ui-warning">
                          <Clock3 size={17} />
                        </div>
                        <div>
                          <p className="text-sm font-semibold">New request received</p>
                          <p className="mt-1 text-xs text-ui-text-muted">
                            A student is interested in a listed resource.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="relative border-l border-ui-border pl-3 sm:pl-4">
                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen((value) => !value);
                    setNotificationsOpen(false);
                  }}
                  className="flex items-center gap-2 rounded-xl p-1.5 transition hover:bg-ui-subtle"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-ui-accent text-xs font-bold text-white">
                    DR
                  </div>
                  <div className="hidden text-left sm:block">
                    <p className="text-xs font-semibold">Student User</p>
                    <p className="text-[10px] text-ui-text-muted">Student</p>
                  </div>
                  <ChevronDown size={15} className="hidden text-ui-text-muted sm:block" />
                </button>

                {profileOpen && (
                  <div className="absolute right-0 top-12 z-50 w-48 rounded-xl border border-ui-border bg-ui-surface p-2 shadow-xl">
                    <button
                      type="button"
                      onClick={() => navigateTo("Settings")}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm hover:bg-ui-subtle"
                    >
                      <Settings size={16} /> Settings
                    </button>
                    <button
                      type="button"
                      onClick={() => navigateTo("Help & Support")}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm hover:bg-ui-subtle"
                    >
                      <CircleHelp size={16} /> Help
                    </button>
                    <div className="my-1 border-t border-ui-border" />
                    <button
                      type="button"
                      onClick={() => navigateTo("Sign out")}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-ui-danger hover:bg-ui-danger-bg"
                    >
                      <LogOut size={16} /> Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </header>

          {/* Page content */}
          <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-7 lg:px-9 lg:py-9">
            {activePage === "Overview" ? (
              <Dashboard
                searchQuery={searchQuery}
                listings={filteredListings}
                onNavigate={navigateTo}
              />
            ) : activePage === "Marketplace" ? (
              <Marketplace onNavigate={navigateTo} />
            ) : activePage === "My Listings" ? (
              <MyListings />
            ) : activePage === "My Requests" ? (
              <MyRequests />
            ) : activePage === "Inventory" ? (
              <Inventory />
            ) : activePage === "Transfers" ? (
              <Transfers />
            ) : activePage === "Analytics" ? (
              <Analytics />
            ) : (
              <ModulePlaceholder
                page={activePage}
                onBack={() => navigateTo("Overview")}
              />
            )}


          </main>
        </div>
      </div>
    </div>
  );
}

function Dashboard({ listings: visibleListings, onNavigate }) {
  const stats = [
    {
      label: "Total resources",
      value: "128",
      change: "+12 this month",
      icon: Package,
      color: "blue",
    },
    {
      label: "Active requests",
      value: "24",
      change: "4 awaiting review",
      icon: BookOpen,
      color: "amber",
    },
    {
      label: "Successful exchanges",
      value: "86",
      change: "+8 this month",
      icon: Handshake,
      color: "green",
    },
    {
      label: "Campus members",
      value: "342",
      change: "Across 3 departments",
      icon: Users,
      color: "blue",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Page heading */}
      <section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-ui-text-muted">
            <span>WORKSPACE</span>
            <span>/</span>
            <span className="text-ui-accent">OVERVIEW</span>
          </div>
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-[34px]">
            Good morning, Student!
          </h2>
          <p className="mt-2 text-sm text-ui-text-secondary">
            Here's what's happening in your campus community today.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onNavigate("My Listings")}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-ui-accent px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-ui-accent-hover"
        >
          <Plus size={17} />
          Add a resource
        </button>
      </section>

      {/* Welcome panel */}
      <section className="relative overflow-hidden rounded-2xl border border-ui-border bg-ui-surface p-6 sm:p-8">
        <div className="relative z-10 max-w-2xl">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-ui-success-bg px-3 py-1.5 text-[11px] font-semibold text-ui-success-text">
            <Recycle size={14} />
            SHARE MORE. WASTE LESS.
          </div>
          <h3 className="font-display text-2xl font-bold leading-tight sm:text-3xl">
            Give your unused resources
            <span className="text-ui-accent"> a new purpose.</span>
          </h3>
          <p className="mt-3 max-w-xl text-sm leading-6 text-ui-text-secondary">
            Help fellow students find the books, equipment and materials they
            need. A small contribution can make a big difference on campus.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => onNavigate("Marketplace")}
              className="inline-flex items-center gap-2 rounded-xl bg-ui-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-ui-accent-hover"
            >
              Explore marketplace <ArrowRight size={16} />
            </button>
            <button
              type="button"
              onClick={() => onNavigate("My Listings")}
              className="rounded-xl border border-ui-border px-4 py-2.5 text-sm font-semibold transition hover:bg-ui-subtle"
            >
              List a resource
            </button>
          </div>
        </div>
        <div className="pointer-events-none absolute -right-10 -top-16 hidden h-72 w-72 items-center justify-center rounded-full border border-ui-border sm:flex">
          <div className="flex h-52 w-52 items-center justify-center rounded-full border border-ui-border">
            <div className="flex h-32 w-32 items-center justify-center rounded-full bg-ui-accent-soft text-ui-accent">
              <Recycle size={68} strokeWidth={1.2} />
            </div>
          </div>
        </div>
      </section>

      {/* Statistics */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="font-display text-lg font-bold">Campus overview</h3>
            <p className="mt-1 text-xs text-ui-text-muted">
              A snapshot of campus resource activity
            </p>
          </div>
          <span className="hidden text-xs text-ui-text-muted sm:block">
            Sample dashboard data
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon;
            const iconClasses = {
              blue: "bg-ui-accent-soft text-ui-accent",
              green: "bg-ui-success-bg text-ui-success",
              amber: "bg-ui-warning-bg text-ui-warning",
            };

            return (
              <article
                key={stat.label}
                className="rounded-2xl border border-ui-border bg-ui-surface p-5"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-medium text-ui-text-secondary">
                      {stat.label}
                    </p>
                    <p className="mt-3 font-display text-3xl font-bold tracking-tight">
                      {stat.value}
                    </p>
                  </div>
                  <div className={`rounded-xl p-3 ${iconClasses[stat.color]}`}>
                    <Icon size={20} strokeWidth={1.8} />
                  </div>
                </div>
                <div className="mt-4 flex items-center gap-1.5 text-xs text-ui-text-muted">
                  {stat.color === "green" ? (
                    <ArrowUpRight size={14} className="text-ui-success" />
                  ) : stat.color === "amber" ? (
                    <Clock3 size={14} className="text-ui-warning" />
                  ) : (
                    <Activity size={14} className="text-ui-accent" />
                  )}
                  {stat.change}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* Main dashboard grid */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,0.85fr)]">
        {/* Recent listings */}
        <section className="min-w-0 rounded-2xl border border-ui-border bg-ui-surface">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ui-border px-5 py-5 sm:px-6">
            <div>
              <h3 className="font-display text-lg font-bold">Recent listings</h3>
              <p className="mt-1 text-xs text-ui-text-muted">
                Recently shared resources from your campus
              </p>
            </div>
            <button
              type="button"
              onClick={() => onNavigate("Marketplace")}
              className="inline-flex items-center gap-1 text-xs font-semibold text-ui-accent hover:underline"
            >
              View marketplace <ArrowRight size={14} />
            </button>
          </div>

          <div className="divide-y divide-ui-border">
            {visibleListings.length > 0 ? (
              visibleListings.map((item) => {
                const Icon = item.icon;
                const iconClasses = {
                  blue: "bg-ui-accent-soft text-ui-accent",
                  green: "bg-ui-success-bg text-ui-success",
                  amber: "bg-ui-warning-bg text-ui-warning",
                };

                return (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 px-5 py-4 transition hover:bg-ui-subtle/60 sm:gap-4 sm:px-6"
                  >
                    <div
                      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconClasses[item.color]}`}
                    >
                      <Icon size={20} />
                    </div>

                    <div className="min-w-0 flex-1">
                      <h4 className="truncate text-sm font-semibold">
                        {item.name}
                      </h4>
                      <p className="mt-1 truncate text-xs text-ui-text-muted">
                        {item.category} · {item.owner}
                      </p>
                    </div>

                    <div className="hidden text-right sm:block">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-semibold ${item.status === "Available"
                          ? "bg-ui-success-bg text-ui-success-text"
                          : "bg-ui-accent-soft text-ui-accent"
                          }`}
                      >
                        {item.status}
                      </span>
                      <p className="mt-1.5 text-[10px] text-ui-text-muted">
                        {item.time}
                      </p>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="px-6 py-12 text-center">
                <Search size={25} className="mx-auto text-ui-text-muted" />
                <p className="mt-3 text-sm font-semibold">No resources found</p>
                <p className="mt-1 text-xs text-ui-text-muted">
                  Try another search term.
                </p>
              </div>
            )}
          </div>

          <div className="border-t border-ui-border px-5 py-4 sm:px-6">
            <button
              type="button"
              onClick={() => onNavigate("Marketplace")}
              className="text-xs font-semibold text-ui-accent hover:underline"
            >
              Explore all resources →
            </button>
          </div>
        </section>

        {/* Activity */}
        <section className="rounded-2xl border border-ui-border bg-ui-surface">
          <div className="border-b border-ui-border px-5 py-5">
            <h3 className="font-display text-lg font-bold">Recent activity</h3>
            <p className="mt-1 text-xs text-ui-text-muted">
              Latest community updates
            </p>
          </div>

          <div className="space-y-5 p-5">
            {activities.map((activity, index) => {
              const Icon = activity.icon;
              const iconClasses = {
                blue: "bg-ui-accent-soft text-ui-accent",
                green: "bg-ui-success-bg text-ui-success",
                amber: "bg-ui-warning-bg text-ui-warning",
              };

              return (
                <div key={activity.title} className="flex gap-3">
                  <div className="relative">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClasses[activity.color]}`}
                    >
                      <Icon size={18} />
                    </div>
                    {index !== activities.length - 1 && (
                      <div className="absolute left-1/2 top-11 h-5 w-px -translate-x-1/2 bg-ui-border" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1 pt-0.5">
                    <p className="text-sm font-semibold">{activity.title}</p>
                    <p className="mt-1 text-xs leading-5 text-ui-text-muted">
                      {activity.detail}
                    </p>
                    <p className="mt-2 text-[10px] text-ui-text-muted">
                      {activity.time}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="border-t border-ui-border px-5 py-4">
            <button
              type="button"
              onClick={() => onNavigate("Analytics")}
              className="text-xs font-semibold text-ui-accent hover:underline"
            >
              View activity insights →
            </button>
          </div>
        </section>
      </div>

      {/* Resource workflow shortcuts */}
      <section>
        <div className="mb-4">
          <h3 className="font-display text-lg font-bold">Quick access</h3>
          <p className="mt-1 text-xs text-ui-text-muted">
            Jump to the main campus workflows
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            {
              title: "Donate a resource",
              description: "Share something another student needs.",
              icon: Recycle,
              page: "My Listings",
            },
            {
              title: "Find an exchange",
              description: "Discover resources available for exchange.",
              icon: Handshake,
              page: "Marketplace",
            },
            {
              title: "Manage requests",
              description: "Review and respond to resource requests.",
              icon: BookOpen,
              page: "My Requests",
            },
            {
              title: "Track transfers",
              description: "Follow resource transfer activity.",
              icon: Truck,
              page: "Transfers",
            },
          ].map((item) => {
            const Icon = item.icon;

            return (
              <button
                type="button"
                key={item.title}
                onClick={() => onNavigate(item.page)}
                className="group flex items-start gap-3 rounded-2xl border border-ui-border bg-ui-surface p-4 text-left transition hover:border-ui-accent/50 hover:bg-ui-subtle"
              >
                <div className="rounded-xl bg-ui-accent-soft p-3 text-ui-accent">
                  <Icon size={19} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{item.title}</p>
                  <p className="mt-1 text-xs leading-5 text-ui-text-muted">
                    {item.description}
                  </p>
                </div>
                <ArrowRight
                  size={16}
                  className="mt-1 shrink-0 text-ui-text-muted transition group-hover:translate-x-1 group-hover:text-ui-accent"
                />
              </button>
            );
          })}
        </div>
      </section>

      <footer className="border-t border-ui-border pt-5 text-center text-xs text-ui-text-muted">
        CampusCycle · Built for students, powered by community.
      </footer>
    </div>
  );
}

const marketplaceResources = [
  {
    id: 1,
    name: "Engineering Mathematics",
    category: "Books",
    type: "Donation",
    condition: "Good",
    owner: "Rahul Sharma",
    department: "Computer Science",
    location: "SRM Campus",
    description:
      "Engineering Mathematics textbook. Good condition with minimal highlighting. Useful for first-year engineering students.",
    icon: BookOpen,
    color: "blue",
    date: "Today",
  },
  {
    id: 2,
    name: "Dell Laptop Stand",
    category: "Electronics",
    type: "Exchange",
    condition: "Like new",
    owner: "Ananya R",
    department: "Information Technology",
    location: "SRM Campus",
    description:
      "Adjustable laptop stand in excellent condition. Looking to exchange for a wireless keyboard or a similar useful accessory.",
    icon: Computer,
    color: "green",
    date: "Today",
  },
  {
    id: 3,
    name: "Chemistry Lab Kit",
    category: "Lab equipment",
    type: "Purchase enquiry",
    condition: "Used",
    owner: "Arjun K",
    department: "Biotechnology",
    location: "SRM Campus",
    description:
      "Basic chemistry laboratory kit. All major components are included. Contact the owner for price and availability details.",
    icon: Package,
    color: "amber",
    date: "Yesterday",
  },
  {
    id: 4,
    name: "Data Structures Notes",
    category: "Study material",
    type: "Donation",
    condition: "Good",
    owner: "Meera S",
    department: "Computer Science",
    location: "SRM Campus",
    description:
      "Organised handwritten notes covering arrays, linked lists, trees, graphs and sorting algorithms.",
    icon: BookOpen,
    color: "blue",
    date: "Yesterday",
  },
  {
    id: 5,
    name: "Scientific Calculator",
    category: "Electronics",
    type: "Purchase enquiry",
    condition: "Good",
    owner: "Karan M",
    department: "Mechanical Engineering",
    location: "SRM Campus",
    description:
      "Scientific calculator suitable for engineering coursework. Enquire with the owner about the asking price.",
    icon: Computer,
    color: "amber",
    date: "2 days ago",
  },
  {
    id: 6,
    name: "Physics Lab Manual",
    category: "Books",
    type: "Exchange",
    condition: "Like new",
    owner: "Priya N",
    department: "Electrical Engineering",
    location: "SRM Campus",
    description:
      "Physics practical manual in very good condition. Interested in exchanging for another engineering textbook.",
    icon: BookOpen,
    color: "green",
    date: "2 days ago",
  },
];

function Marketplace({ onNavigate }) {
  const [query, setQuery] = useState("");
  const [selectedType, setSelectedType] = useState("All");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [selectedResource, setSelectedResource] = useState(null);
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const categories = [
    "All",
    "Books",
    "Electronics",
    "Lab equipment",
    "Study material",
  ];

  const types = [
    "All",
    "Donation",
    "Exchange",
    "Purchase enquiry",
  ];

  const filteredResources = marketplaceResources.filter((resource) => {
    const matchesQuery = [
      resource.name,
      resource.category,
      resource.owner,
      resource.department,
    ]
      .join(" ")
      .toLowerCase()
      .includes(query.toLowerCase().trim());

    const matchesType =
      selectedType === "All" || resource.type === selectedType;

    const matchesCategory =
      selectedCategory === "All" ||
      resource.category === selectedCategory;

    return matchesQuery && matchesType && matchesCategory;
  });

  function openResource(resource) {
    setSelectedResource(resource);
    setMessage("");
    setSubmitted(false);
  }

  function closeResource() {
    setSelectedResource(null);
    setMessage("");
    setSubmitted(false);
  }

  function submitEnquiry(event) {
    event.preventDefault();

    if (!message.trim()) return;

    setSubmitted(true);
  }

 

  return (
    <div className="space-y-7">
      {/* Page heading */}
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-ui-text-muted">
            <span>WORKSPACE</span>
            <span>/</span>
            <span className="text-ui-accent">MARKETPLACE</span>
          </div>

          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-[34px]">
            Campus marketplace
          </h2>

          <p className="mt-2 max-w-xl text-sm leading-6 text-ui-text-secondary">
            Discover useful resources shared by students across your campus.
            Find something you need or give an unused resource a new purpose.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onNavigate("My Listings")}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-ui-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-ui-accent-hover"
        >
          <Plus size={17} />
          List a resource
        </button>
      </section>

      {/* Marketplace information */}
      <section className="grid gap-3 sm:grid-cols-3">
        {[
          {
            title: "Donate",
            description: "Share resources for free.",
            icon: Recycle,
            color: "green",
          },
          {
            title: "Exchange",
            description: "Trade resources with students.",
            icon: Handshake,
            color: "blue",
          },
          {
            title: "Purchase enquiry",
            description: "Contact owners about buying.",
            icon: ShoppingBag,
            color: "amber",
          },
        ].map((item) => {
          const Icon = item.icon;
          const styles = {
            green: "bg-ui-success-bg text-ui-success",
            blue: "bg-ui-accent-soft text-ui-accent",
            amber: "bg-ui-warning-bg text-ui-warning",
          };

          return (
            <div
              key={item.title}
              className="flex items-center gap-3 rounded-2xl border border-ui-border bg-ui-surface p-4"
            >
              <div className={`rounded-xl p-3 ${styles[item.color]}`}>
                <Icon size={21} />
              </div>
              <div>
                <p className="text-sm font-semibold">{item.title}</p>
                <p className="mt-1 text-xs text-ui-text-muted">
                  {item.description}
                </p>
              </div>
            </div>
          );
        })}
      </section>

      {/* Search and filters */}
      <section className="rounded-2xl border border-ui-border bg-ui-surface p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
          <div className="relative min-w-0 flex-1">
            <Search
              size={18}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ui-text-muted"
            />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by resource, category or student..."
              className="h-11 w-full rounded-xl border border-ui-border bg-ui-canvas pl-10 pr-4 text-sm outline-none transition placeholder:text-ui-text-muted focus:border-ui-focus focus:ring-2 focus:ring-ui-focus/15"
            />
          </div>

          <div className="flex items-center gap-2">
            <SlidersHorizontal size={17} className="text-ui-text-muted" />
            <select
              value={selectedCategory}
              onChange={(event) => setSelectedCategory(event.target.value)}
              className="h-11 min-w-0 flex-1 rounded-xl border border-ui-border bg-ui-canvas px-3 text-sm outline-none focus:border-ui-focus sm:min-w-[180px]"
              aria-label="Filter by category"
            >
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category === "All" ? "All categories" : category}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-5">
          <p className="mb-3 text-xs font-semibold text-ui-text-secondary">
            LISTING TYPE
          </p>

          <div className="flex flex-wrap gap-2">
            {types.map((type) => (
              <button
                type="button"
                key={type}
                onClick={() => setSelectedType(type)}
                className={`rounded-xl px-4 py-2.5 text-xs font-semibold transition ${selectedType === type
                  ? "bg-ui-accent text-white"
                  : "border border-ui-border bg-ui-surface text-ui-text-secondary hover:bg-ui-subtle"
                  }`}
              >
                {type === "All" ? "All listings" : type}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Results heading */}
      <section>
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-display text-lg font-bold">
              Explore resources
            </h3>
            <p className="mt-1 text-xs text-ui-text-muted">
              {filteredResources.length} resources found
            </p>
          </div>
          <span className="text-xs text-ui-text-muted">
            Sample marketplace listings
          </span>
        </div>

        {filteredResources.length > 0 ? (
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {filteredResources.map((resource) => {
              const Icon = resource.icon;
              const iconStyles = {
                blue: "bg-ui-accent-soft text-ui-accent",
                green: "bg-ui-success-bg text-ui-success",
                amber: "bg-ui-warning-bg text-ui-warning",
              };

              return (
                <article
                  key={resource.id}
                  className="group flex flex-col overflow-hidden rounded-2xl border border-ui-border bg-ui-surface transition hover:-translate-y-1 hover:border-ui-accent/40 hover:shadow-lg"
                >
                  <div className="flex h-36 items-center justify-center bg-ui-subtle">
                    <div
                      className={`flex h-16 w-16 items-center justify-center rounded-2xl ${iconStyles[resource.color]}`}
                    >
                      <Icon size={31} strokeWidth={1.5} />
                    </div>
                  </div>

                  <div className="flex flex-1 flex-col p-5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-medium text-ui-text-muted">
                        {resource.category}
                      </span>
                      <span
                        className={`rounded-full px-3 py-1 text-[10px] font-semibold ${typeStyles[resource.type]}`}
                      >
                        {resource.type}
                      </span>
                    </div>

                    <h4 className="mt-3 font-display text-lg font-bold">
                      {resource.name}
                    </h4>

                    <p className="mt-1 text-xs text-ui-text-secondary">
                      Condition: {resource.condition}
                    </p>

                    <div className="mt-4 space-y-2 border-t border-ui-border pt-4">
                      <div className="flex items-center gap-2 text-xs text-ui-text-muted">
                        <UserRound size={14} />
                        {resource.owner}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-ui-text-muted">
                        <MapPin size={14} />
                        {resource.location}
                      </div>
                    </div>

                    <div className="mt-auto flex items-center justify-between gap-3 pt-5">
                      <span className="text-[11px] text-ui-text-muted">
                        {resource.date}
                      </span>
                      <button
                        type="button"
                        onClick={() => openResource(resource)}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-ui-accent px-3.5 py-2.5 text-xs font-semibold text-white transition hover:bg-ui-accent-hover"
                      >
                        View details <ArrowRight size={14} />
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-ui-border bg-ui-surface px-6 py-16 text-center">
            <Search size={30} className="mx-auto text-ui-text-muted" />
            <h4 className="mt-4 font-display text-lg font-bold">
              No matching resources
            </h4>
            <p className="mt-2 text-sm text-ui-text-muted">
              Try changing your search or filters.
            </p>
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setSelectedType("All");
                setSelectedCategory("All");
              }}
              className="mt-5 text-sm font-semibold text-ui-accent hover:underline"
            >
              Clear all filters
            </button>
          </div>
        )}
      </section>

      {/* Resource detail and enquiry dialog */}
      {selectedResource && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center overflow-y-auto bg-black/55 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeResource();
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="resource-dialog-title"
            className="my-auto w-full max-w-xl rounded-2xl border border-ui-border bg-ui-surface p-6 shadow-2xl sm:p-7"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold text-ui-accent">
                  RESOURCE DETAILS
                </p>
                <h3
                  id="resource-dialog-title"
                  className="mt-2 font-display text-2xl font-bold"
                >
                  {selectedResource.name}
                </h3>
              </div>

              <button
                type="button"
                onClick={closeResource}
                className="rounded-lg p-2 text-ui-text-muted hover:bg-ui-subtle"
                aria-label="Close details"
              >
                <X size={20} />
              </button>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full bg-ui-accent-soft px-3 py-1.5 text-xs font-semibold text-ui-accent">
                {selectedResource.category}
              </span>
              <span
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${typeStyles[selectedResource.type]}`}
              >
                {selectedResource.type}
              </span>
            </div>

            <p className="mt-5 text-sm leading-6 text-ui-text-secondary">
              {selectedResource.description}
            </p>

            <div className="mt-5 grid grid-cols-2 gap-4 rounded-xl bg-ui-subtle p-4">
              <div>
                <p className="text-[11px] text-ui-text-muted">Listed by</p>
                <p className="mt-1 text-sm font-semibold">
                  {selectedResource.owner}
                </p>
              </div>
              <div>
                <p className="text-[11px] text-ui-text-muted">Condition</p>
                <p className="mt-1 text-sm font-semibold">
                  {selectedResource.condition}
                </p>
              </div>
              <div>
                <p className="text-[11px] text-ui-text-muted">Department</p>
                <p className="mt-1 text-sm font-semibold">
                  {selectedResource.department}
                </p>
              </div>
              <div>
                <p className="text-[11px] text-ui-text-muted">Location</p>
                <p className="mt-1 text-sm font-semibold">
                  {selectedResource.location}
                </p>
              </div>
            </div>

            {submitted ? (
              <div className="mt-6 rounded-xl border border-ui-border bg-ui-success-bg p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-ui-success-text">
                  <CheckCircle2 size={19} />
                  Demo interaction completed
                </div>
                <p className="mt-2 text-xs leading-5 text-ui-success-text">
                  Your message was accepted by this frontend demonstration.
                  It has not been sent to the owner or saved to a database.
                </p>
                <button
                  type="button"
                  onClick={closeResource}
                  className="mt-4 text-sm font-semibold text-ui-accent hover:underline"
                >
                  Close
                </button>
              </div>
            ) : (
              <form onSubmit={submitEnquiry} className="mt-6">
                <label
                  htmlFor="marketplace-message"
                  className="text-sm font-semibold"
                >
                  {selectedResource.type === "Donation"
                    ? "Why do you need this resource?"
                    : selectedResource.type === "Exchange"
                      ? "What would you offer in exchange?"
                      : "Your purchase enquiry"}
                </label>

                <textarea
                  id="marketplace-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  required
                  rows={3}
                  maxLength={500}
                  placeholder={
                    selectedResource.type === "Donation"
                      ? "Introduce yourself and explain why you need this resource..."
                      : selectedResource.type === "Exchange"
                        ? "Describe the resource you would like to offer..."
                        : "Ask the owner about the price and availability..."
                  }
                  className="mt-2 w-full resize-y rounded-xl border border-ui-border bg-ui-canvas p-3 text-sm outline-none placeholder:text-ui-text-muted focus:border-ui-focus focus:ring-2 focus:ring-ui-focus/15"
                />

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <p className="max-w-[220px] text-[11px] leading-5 text-ui-text-muted">
                    {selectedResource.type === "Purchase enquiry"
                      ? "Payment arrangements happen outside CampusCycle."
                      : "This is a demonstration; no real request will be sent."}
                  </p>

                  <button
                    type="submit"
                    className="inline-flex items-center gap-2 rounded-xl bg-ui-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-ui-accent-hover"
                  >
                    <Send size={16} />
                    {selectedResource.type === "Donation"
                      ? "Request resource"
                      : selectedResource.type === "Exchange"
                        ? "Propose exchange"
                        : "Send enquiry"}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}
    </div>
  );
}


const initialMyListings = [
  {
    id: 101,
    name: "Engineering Mathematics",
    category: "Books",
    type: "Donation",
    condition: "Good",
    description: "Engineering Mathematics textbook with minimal highlighting.",
    status: "Available",
  },
  {
    id: 102,
    name: "Dell Laptop Stand",
    category: "Electronics",
    type: "Exchange",
    condition: "Like new",
    description: "Adjustable laptop stand. Looking for a keyboard in exchange.",
    status: "Available",
  },
  {
    id: 103,
    name: "Chemistry Lab Kit",
    category: "Lab equipment",
    type: "Purchase enquiry",
    condition: "Used",
    description: "Basic chemistry laboratory kit. Contact for price details.",
    status: "Reserved",
  },
];

const emptyListingForm = {
  name: "",
  category: "",
  type: "Donation",
  condition: "Good",
  description: "",
};

function MyListings() {
  const [myListings, setMyListings] = useState(initialMyListings);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [filter, setFilter] = useState("All");
  const [query, setQuery] = useState("");
  const [form, setForm] = useState(emptyListingForm);
  const [formError, setFormError] = useState("");

  const availableCount = myListings.filter(
    (item) => item.status === "Available"
  ).length;

  const reservedCount = myListings.filter(
    (item) => item.status === "Reserved"
  ).length;

  const filteredListings = myListings.filter((item) => {
    const matchesQuery = [
      item.name,
      item.category,
      item.type,
      item.description,
    ]
      .join(" ")
      .toLowerCase()
      .includes(query.trim().toLowerCase());

    const matchesFilter =
      filter === "All" || item.status === filter;

    return matchesQuery && matchesFilter;
  });

  function startCreate() {
    setForm(emptyListingForm);
    setEditingId(null);
    setFormError("");
    setShowForm(true);
  }

  function startEdit(listing) {
    setForm({
      name: listing.name,
      category: listing.category,
      type: listing.type,
      condition: listing.condition,
      description: listing.description,
    });
    setEditingId(listing.id);
    setFormError("");
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(emptyListingForm);
    setFormError("");
  }

  function handleFormChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (
      !form.name.trim() ||
      !form.category ||
      !form.description.trim()
    ) {
      setFormError("Please complete all required fields.");
      return;
    }

    if (form.description.trim().length < 10) {
      setFormError("Description must contain at least 10 characters.");
      return;
    }

    if (editingId !== null) {
      setMyListings((current) =>
        current.map((item) =>
          item.id === editingId
            ? { ...item, ...form }
            : item
        )
      );
    } else {
      setMyListings((current) => [
        {
          id: Date.now(),
          ...form,
          status: "Available",
        },
        ...current,
      ]);
    }

    closeForm();
  }

  function deleteListing(id) {
    const listing = myListings.find((item) => item.id === id);

    if (!listing) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete "${listing.name}"?`
    );

    if (!confirmed) return;

    setMyListings((current) =>
      current.filter((item) => item.id !== id)
    );
  }

 

  return (
    <div className="space-y-7">
      {/* Page heading */}
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-ui-text-muted">
            <span>WORKSPACE</span>
            <span>/</span>
            <span className="text-ui-accent">MY LISTINGS</span>
          </div>

          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-[34px]">
            My listings
          </h2>

          <p className="mt-2 max-w-xl text-sm leading-6 text-ui-text-secondary">
            Manage the resources you've shared with your campus community.
            Keep your listings accurate and up to date.
          </p>
        </div>

        <button
          type="button"
          onClick={startCreate}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-ui-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-ui-accent-hover"
        >
          <Plus size={17} />
          Create listing
        </button>
      </section>

      {/* Summary cards */}
      <section className="grid gap-4 sm:grid-cols-3">
        {[
          {
            label: "Total listings",
            value: myListings.length,
            icon: Package,
            color: "blue",
          },
          {
            label: "Available",
            value: availableCount,
            icon: CheckCircle2,
            color: "green",
          },
          {
            label: "Reserved",
            value: reservedCount,
            icon: Clock3,
            color: "amber",
          },
        ].map((stat) => {
          const Icon = stat.icon;
          const styles = {
            blue: "bg-ui-accent-soft text-ui-accent",
            green: "bg-ui-success-bg text-ui-success",
            amber: "bg-ui-warning-bg text-ui-warning",
          };

          return (
            <article
              key={stat.label}
              className="rounded-2xl border border-ui-border bg-ui-surface p-5"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-ui-text-secondary">
                  {stat.label}
                </p>
                <div className={`rounded-xl p-2.5 ${styles[stat.color]}`}>
                  <Icon size={19} />
                </div>
              </div>
              <p className="mt-3 font-display text-3xl font-bold">
                {stat.value}
              </p>
            </article>
          );
        })}
      </section>

      {/* Create and edit form */}
      {showForm && (
        <section className="rounded-2xl border border-ui-border bg-ui-surface p-5 sm:p-7">
          <div className="mb-6 flex items-center justify-between gap-3">
            <div>
              <h3 className="font-display text-xl font-bold">
                {editingId !== null ? "Edit listing" : "Create a listing"}
              </h3>
              <p className="mt-1 text-xs text-ui-text-muted">
                Provide accurate information about your resource.
              </p>
            </div>

            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg p-2 text-ui-text-muted hover:bg-ui-subtle"
              aria-label="Close form"
            >
              <X size={19} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid gap-5 sm:grid-cols-2">
              <label className="text-sm font-semibold">
                Resource name *
                <input
                  name="name"
                  value={form.name}
                  onChange={handleFormChange}
                  maxLength={100}
                  required
                  placeholder="e.g. Engineering Mathematics"
                  className="mt-2 h-11 w-full rounded-xl border border-ui-border bg-ui-canvas px-3 text-sm font-normal outline-none focus:border-ui-focus"
                />
              </label>

              <label className="text-sm font-semibold">
                Category *
                <select
                  name="category"
                  value={form.category}
                  onChange={handleFormChange}
                  required
                  className="mt-2 h-11 w-full rounded-xl border border-ui-border bg-ui-canvas px-3 text-sm font-normal outline-none focus:border-ui-focus"
                >
                  <option value="">Select category</option>
                  <option value="Books">Books</option>
                  <option value="Electronics">Electronics</option>
                  <option value="Lab equipment">Lab equipment</option>
                  <option value="Study material">Study material</option>
                  <option value="Other">Other</option>
                </select>
              </label>

              <label className="text-sm font-semibold">
                Listing type *
                <select
                  name="type"
                  value={form.type}
                  onChange={handleFormChange}
                  className="mt-2 h-11 w-full rounded-xl border border-ui-border bg-ui-canvas px-3 text-sm font-normal outline-none focus:border-ui-focus"
                >
                  <option value="Donation">Donation</option>
                  <option value="Exchange">Exchange</option>
                  <option value="Purchase enquiry">Purchase enquiry</option>
                </select>
              </label>

              <label className="text-sm font-semibold">
                Resource condition *
                <select
                  name="condition"
                  value={form.condition}
                  onChange={handleFormChange}
                  className="mt-2 h-11 w-full rounded-xl border border-ui-border bg-ui-canvas px-3 text-sm font-normal outline-none focus:border-ui-focus"
                >
                  <option value="New">New</option>
                  <option value="Like new">Like new</option>
                  <option value="Good">Good</option>
                  <option value="Used">Used</option>
                </select>
              </label>
            </div>

            <label className="block text-sm font-semibold">
              Description *
              <textarea
                name="description"
                value={form.description}
                onChange={handleFormChange}
                required
                minLength={10}
                maxLength={1000}
                rows={4}
                placeholder="Describe the resource, its condition and any relevant details..."
                className="mt-2 w-full rounded-xl border border-ui-border bg-ui-canvas p-3 text-sm font-normal outline-none focus:border-ui-focus"
              />
              <span className="mt-1 block text-right text-[11px] font-normal text-ui-text-muted">
                {form.description.length}/1000 characters
              </span>
            </label>

            {form.type === "Exchange" && (
              <div className="rounded-xl bg-ui-accent-soft p-3 text-xs leading-5 text-ui-accent">
                Describe what you would like in return in the resource
                description. Exchange arrangements will be handled through
                the request workflow.
              </div>
            )}

            {form.type === "Purchase enquiry" && (
              <div className="rounded-xl bg-ui-warning-bg p-3 text-xs leading-5 text-ui-warning-text">
                Students can enquire about purchasing this resource.
                Price discussions and payments take place outside CampusCycle.
              </div>
            )}

            {formError && (
              <p role="alert" className="text-sm font-medium text-ui-danger">
                {formError}
              </p>
            )}

            <div className="flex flex-wrap justify-end gap-3 border-t border-ui-border pt-5">
              <button
                type="button"
                onClick={closeForm}
                className="rounded-xl border border-ui-border px-4 py-2.5 text-sm font-semibold hover:bg-ui-subtle"
              >
                Cancel
              </button>

              <button
                type="submit"
                className="inline-flex items-center gap-2 rounded-xl bg-ui-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-ui-accent-hover"
              >
                <Save size={16} />
                {editingId !== null ? "Save changes" : "Publish listing"}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Search and filters */}
      <section className="rounded-2xl border border-ui-border bg-ui-surface p-4 sm:p-5">
        <div className="relative">
          <Search
            size={17}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ui-text-muted"
          />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search your listings..."
            className="h-11 w-full rounded-xl border border-ui-border bg-ui-canvas pl-10 pr-4 text-sm outline-none focus:border-ui-focus"
          />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {["All", "Available", "Reserved"].map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setFilter(status)}
              className={`rounded-xl px-4 py-2.5 text-xs font-semibold transition ${filter === status
                ? "bg-ui-accent text-white"
                : "border border-ui-border text-ui-text-secondary hover:bg-ui-subtle"
                }`}
            >
              {status}
            </button>
          ))}
        </div>
      </section>

      {/* Listing table */}
      <section className="overflow-hidden rounded-2xl border border-ui-border bg-ui-surface">
        <div className="flex items-center justify-between gap-3 border-b border-ui-border px-5 py-5">
          <div>
            <h3 className="font-display text-lg font-bold">
              Your resources
            </h3>
            <p className="mt-1 text-xs text-ui-text-muted">
              {filteredListings.length} listings displayed
            </p>
          </div>
        </div>

        {filteredListings.length > 0 ? (
          <div className="divide-y divide-ui-border">
            {filteredListings.map((listing) => (
              <article
                key={listing.id}
                className="flex flex-col gap-4 px-5 py-5 transition hover:bg-ui-subtle/50 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 items-start gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-ui-accent-soft text-ui-accent">
                    <Package size={21} />
                  </div>

                  <div className="min-w-0">
                    <h4 className="truncate text-sm font-semibold">
                      {listing.name}
                    </h4>
                    <p className="mt-1 text-xs text-ui-text-muted">
                      {listing.category} · {listing.condition}
                    </p>
                    <p className="mt-2 text-xs text-ui-text-secondary">
                      {listing.type}
                    </p>
                    <p className="mt-2 line-clamp-2 text-xs leading-5 text-ui-text-muted">
                      {listing.description}
                    </p>
                  </div>
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
                  <span
                    className={`rounded-full px-3 py-1.5 text-[10px] font-semibold ${listing.status === "Available"
                      ? "bg-ui-success-bg text-ui-success-text"
                      : "bg-ui-accent-soft text-ui-accent"
                      }`}
                  >
                    {listing.status}
                  </span>

                  <button
                    type="button"
                    onClick={() => startEdit(listing)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-ui-border px-3 py-2 text-xs font-semibold hover:bg-ui-subtle"
                  >
                    <Pencil size={14} />
                    Edit
                  </button>

                  <button
                    type="button"
                    onClick={() => deleteListing(listing.id)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-ui-border px-3 py-2 text-xs font-semibold text-ui-danger hover:bg-ui-danger-bg"
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="px-6 py-14 text-center">
            <Package size={30} className="mx-auto text-ui-text-muted" />
            <h4 className="mt-3 font-display font-bold">
              No listings found
            </h4>
            <p className="mt-2 text-sm text-ui-text-muted">
              Try another search or create a new resource listing.
            </p>
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setFilter("All");
              }}
              className="mt-4 text-sm font-semibold text-ui-accent hover:underline"
            >
              Clear filters
            </button>
          </div>
        )}
      </section>
    </div>
  );
}


const initialRequests = [
  {
    id: 201,
    direction: "Received",
    resource: "Engineering Mathematics",
    type: "Donation",
    from: "Aarav Kumar",
    department: "Computer Science",
    message: "I need this textbook for my upcoming semester.",
    status: "Pending",
    date: "Today",
  },
  {
    id: 202,
    direction: "Received",
    resource: "Dell Laptop Stand",
    type: "Exchange",
    from: "Sneha R",
    department: "Information Technology",
    message: "I can offer a wireless keyboard in exchange.",
    status: "Pending",
    date: "Today",
  },
  {
    id: 203,
    direction: "Received",
    resource: "Chemistry Lab Kit",
    type: "Purchase enquiry",
    from: "Rahul S",
    department: "Biotechnology",
    message: "Could you share the expected price and availability?",
    status: "Approved",
    date: "Yesterday",
  },
  {
    id: 204,
    direction: "Sent",
    resource: "Physics Lab Manual",
    type: "Exchange",
    from: "Priya N",
    department: "Electrical Engineering",
    message: "I can offer my previous semester lab notes.",
    status: "Pending",
    date: "Today",
  },
  {
    id: 205,
    direction: "Sent",
    resource: "Data Structures Notes",
    type: "Donation",
    from: "Meera S",
    department: "Computer Science",
    message: "I would like to request these study notes.",
    status: "Rejected",
    date: "Yesterday",
  },
];

function MyRequests() {
  const [requests, setRequests] = useState(initialRequests);
  const [activeTab, setActiveTab] = useState("Received");
  const [statusFilter, setStatusFilter] = useState("All");
  const [query, setQuery] = useState("");
  const [selectedRequest, setSelectedRequest] = useState(null);

  const pendingCount = requests.filter(
    (request) =>
      request.direction === "Received" &&
      request.status === "Pending"
  ).length;

  const approvedCount = requests.filter(
    (request) => request.status === "Approved"
  ).length;

  const rejectedCount = requests.filter(
    (request) => request.status === "Rejected"
  ).length;

  const filteredRequests = requests.filter((request) => {
    const matchesDirection = request.direction === activeTab;

    const matchesStatus =
      statusFilter === "All" || request.status === statusFilter;

    const matchesSearch = [
      request.resource,
      request.from,
      request.type,
      request.department,
      request.message,
    ]
      .join(" ")
      .toLowerCase()
      .includes(query.trim().toLowerCase());

    return matchesDirection && matchesStatus && matchesSearch;
  });

  function updateRequestStatus(id, newStatus) {
    setRequests((current) =>
      current.map((request) =>
        request.id === id
          ? { ...request, status: newStatus }
          : request
      )
    );

    setSelectedRequest(null);
  }

  const statusStyles = {
    Pending: "bg-ui-warning-bg text-ui-warning-text",
    Approved: "bg-ui-success-bg text-ui-success-text",
    Rejected: "bg-ui-danger-bg text-ui-danger",
  };


  return (
    <div className="space-y-7">
      {/* Page heading */}
      <section>
        <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-ui-text-muted">
          <span>WORKSPACE</span>
          <span>/</span>
          <span className="text-ui-accent">MY REQUESTS</span>
        </div>

        <h2 className="font-display text-3xl font-bold tracking-tight sm:text-[34px]">
          My requests
        </h2>

        <p className="mt-2 max-w-xl text-sm leading-6 text-ui-text-secondary">
          Review requests received for your resources and track the
          requests you've sent to other students.
        </p>
      </section>

      {/* Summary */}
      <section className="grid gap-4 sm:grid-cols-3">
        {[
          {
            label: "Pending received",
            value: pendingCount,
            icon: Clock3,
            color: "amber",
          },
          {
            label: "Approved",
            value: approvedCount,
            icon: CheckCircle2,
            color: "green",
          },
          {
            label: "Rejected",
            value: rejectedCount,
            icon: X,
            color: "red",
          },
        ].map((item) => {
          const Icon = item.icon;
          const styles = {
            amber: "bg-ui-warning-bg text-ui-warning",
            green: "bg-ui-success-bg text-ui-success",
            red: "bg-ui-danger-bg text-ui-danger",
          };

          return (
            <article
              key={item.label}
              className="rounded-2xl border border-ui-border bg-ui-surface p-5"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-ui-text-secondary">
                  {item.label}
                </p>
                <div className={`rounded-xl p-2.5 ${styles[item.color]}`}>
                  <Icon size={19} />
                </div>
              </div>
              <p className="mt-3 font-display text-3xl font-bold">
                {item.value}
              </p>
            </article>
          );
        })}
      </section>

      {/* Received and sent tabs */}
      <section className="rounded-2xl border border-ui-border bg-ui-surface p-4 sm:p-5">
        <div className="flex flex-wrap gap-2">
          {["Received", "Sent"].map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => {
                setActiveTab(tab);
                setStatusFilter("All");
                setSelectedRequest(null);
              }}
              className={`rounded-xl px-5 py-3 text-sm font-semibold transition ${activeTab === tab
                ? "bg-ui-accent text-white"
                : "border border-ui-border text-ui-text-secondary hover:bg-ui-subtle"
                }`}
            >
              {tab === "Received" ? "Received requests" : "Sent requests"}
              <span className="ml-2 text-xs opacity-75">
                ({requests.filter((r) => r.direction === tab).length})
              </span>
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative mt-5">
          <Search
            size={17}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ui-text-muted"
          />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by resource or student..."
            className="h-11 w-full rounded-xl border border-ui-border bg-ui-canvas pl-10 pr-4 text-sm outline-none focus:border-ui-focus"
          />
        </div>

        {/* Status filters */}
        <div className="mt-4 flex flex-wrap gap-2">
          {["All", "Pending", "Approved", "Rejected"].map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
              className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition ${statusFilter === status
                ? "bg-ui-accent text-white"
                : "border border-ui-border text-ui-text-secondary hover:bg-ui-subtle"
                }`}
            >
              {status}
            </button>
          ))}
        </div>
      </section>

      {/* Request list */}
      <section className="overflow-hidden rounded-2xl border border-ui-border bg-ui-surface">
        <div className="border-b border-ui-border px-5 py-5">
          <h3 className="font-display text-lg font-bold">
            {activeTab === "Received"
              ? "Requests received"
              : "Requests sent"}
          </h3>
          <p className="mt-1 text-xs text-ui-text-muted">
            {filteredRequests.length} requests displayed
          </p>
        </div>

        {filteredRequests.length > 0 ? (
          <div className="divide-y divide-ui-border">
            {filteredRequests.map((request) => (
              <article
                key={request.id}
                className="flex flex-col gap-4 p-5 transition hover:bg-ui-subtle/40"
              >
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div className="flex min-w-0 gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-ui-accent-soft text-ui-accent">
                      <Package size={21} />
                    </div>

                    <div className="min-w-0">
                      <h4 className="font-semibold">
                        {request.resource}
                      </h4>

                      <p className="mt-1 text-xs text-ui-text-secondary">
                        {activeTab === "Received" ? "From" : "Owner"}:{" "}
                        {request.from}
                      </p>

                      <p className="mt-1 text-xs text-ui-text-muted">
                        {request.department} · {request.date}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <span
                      className={`rounded-full px-3 py-1.5 text-[10px] font-semibold ${typeStyles[request.type]}`}
                    >
                      {request.type}
                    </span>
                    <span
                      className={`rounded-full px-3 py-1.5 text-[10px] font-semibold ${statusStyles[request.status]}`}
                    >
                      {request.status}
                    </span>
                  </div>
                </div>

                <div className="rounded-xl bg-ui-subtle p-4">
                  <p className="text-[11px] font-semibold text-ui-text-muted">
                    MESSAGE
                  </p>
                  <p className="mt-2 text-sm leading-6 text-ui-text-secondary">
                    {request.message}
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => setSelectedRequest(request)}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-ui-accent hover:underline"
                  >
                    View request details <ArrowRight size={14} />
                  </button>

                  {activeTab === "Received" &&
                    request.status === "Pending" && (
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            updateRequestStatus(request.id, "Rejected")
                          }
                          className="rounded-lg border border-ui-border px-3.5 py-2 text-xs font-semibold text-ui-danger hover:bg-ui-danger-bg"
                        >
                          Reject
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            updateRequestStatus(request.id, "Approved")
                          }
                          className="rounded-lg bg-ui-success px-3.5 py-2 text-xs font-semibold text-white hover:opacity-90"
                        >
                          Approve
                        </button>
                      </div>
                    )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="px-6 py-14 text-center">
            <Package size={30} className="mx-auto text-ui-text-muted" />
            <h4 className="mt-3 font-display font-bold">
              No requests found
            </h4>
            <p className="mt-2 text-sm text-ui-text-muted">
              Try another search, status or request tab.
            </p>
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setStatusFilter("All");
              }}
              className="mt-4 text-sm font-semibold text-ui-accent hover:underline"
            >
              Clear filters
            </button>
          </div>
        )}
      </section>

      {/* Request detail dialog */}
      {selectedRequest && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center overflow-y-auto bg-black/55 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedRequest(null);
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="request-dialog-title"
            className="my-auto w-full max-w-lg rounded-2xl border border-ui-border bg-ui-surface p-6 shadow-2xl"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-ui-accent">
                  REQUEST DETAILS
                </p>
                <h3
                  id="request-dialog-title"
                  className="mt-2 font-display text-xl font-bold"
                >
                  {selectedRequest.resource}
                </h3>
              </div>

              <button
                type="button"
                onClick={() => setSelectedRequest(null)}
                className="rounded-lg p-2 text-ui-text-muted hover:bg-ui-subtle"
                aria-label="Close details"
              >
                <X size={19} />
              </button>
            </div>

            <div className="mt-5 space-y-4">
              <div>
                <p className="text-xs text-ui-text-muted">Student</p>
                <p className="mt-1 text-sm font-semibold">
                  {selectedRequest.from}
                </p>
              </div>
              <div>
                <p className="text-xs text-ui-text-muted">Department</p>
                <p className="mt-1 text-sm font-semibold">
                  {selectedRequest.department}
                </p>
              </div>
              <div>
                <p className="text-xs text-ui-text-muted">Request type</p>
                <p className="mt-1 text-sm font-semibold">
                  {selectedRequest.type}
                </p>
              </div>
              <div>
                <p className="text-xs text-ui-text-muted">Message</p>
                <p className="mt-1 rounded-xl bg-ui-subtle p-4 text-sm leading-6 text-ui-text-secondary">
                  {selectedRequest.message}
                </p>
              </div>
              <div>
                <p className="text-xs text-ui-text-muted">Current status</p>
                <span
                  className={`mt-2 inline-flex rounded-full px-3 py-1.5 text-xs font-semibold ${statusStyles[selectedRequest.status]}`}
                >
                  {selectedRequest.status}
                </span>
              </div>
            </div>

            {selectedRequest.direction === "Received" &&
              selectedRequest.status === "Pending" && (
                <div className="mt-6 flex justify-end gap-2 border-t border-ui-border pt-5">
                  <button
                    type="button"
                    onClick={() =>
                      updateRequestStatus(selectedRequest.id, "Rejected")
                    }
                    className="rounded-xl border border-ui-border px-4 py-2.5 text-sm font-semibold text-ui-danger"
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      updateRequestStatus(selectedRequest.id, "Approved")
                    }
                    className="rounded-xl bg-ui-success px-4 py-2.5 text-sm font-semibold text-white"
                  >
                    Approve
                  </button>
                </div>
              )}
          </section>
        </div>
      )}
    </div>
  );
}


function Inventory() {
  const [resources, setResources] = useState([
    {
      id: 1,
      name: "Engineering Mathematics",
      category: "Books",
      owner: "Rahul Sharma",
      quantity: 5,
      reserved: 1,
      location: "Computer Science",
    },
    {
      id: 2,
      name: "Dell Laptop Stand",
      category: "Electronics",
      owner: "Ananya R",
      quantity: 3,
      reserved: 0,
      location: "Information Technology",
    },
    {
      id: 3,
      name: "Chemistry Lab Kit",
      category: "Lab equipment",
      owner: "Arjun K",
      quantity: 4,
      reserved: 4,
      location: "Biotechnology",
    },
    {
      id: 4,
      name: "Data Structures Notes",
      category: "Study material",
      owner: "Meera S",
      quantity: 10,
      reserved: 2,
      location: "Computer Science",
    },
    {
      id: 5,
      name: "Scientific Calculator",
      category: "Electronics",
      owner: "Karan M",
      quantity: 6,
      reserved: 1,
      location: "Electronics",
    },
  ]);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const getStatus = (item) => {
    if (item.reserved >= item.quantity) return "Fully Reserved";
    if (item.reserved > 0) return "Partially Reserved";
    return "Available";
  };

  const filteredResources = resources.filter((item) => {
    const matchesSearch =
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.category.toLowerCase().includes(search.toLowerCase()) ||
      item.owner.toLowerCase().includes(search.toLowerCase());

    const status = getStatus(item);

    const matchesStatus =
      statusFilter === "All" ||
      (statusFilter === "Available" && item.reserved < item.quantity) ||
      (statusFilter === "Fully Reserved" && status === "Fully Reserved");

    return matchesSearch && matchesStatus;
  });

  const totalQuantity = resources.reduce(
    (sum, item) => sum + item.quantity,
    0
  );

  const totalReserved = resources.reduce(
    (sum, item) => sum + item.reserved,
    0
  );

  const availableQuantity = totalQuantity - totalReserved;

  const updateReservation = (id, action) => {
    setResources((current) =>
      current.map((item) => {
        if (item.id !== id) return item;

        if (action === "reserve" && item.reserved < item.quantity) {
          return { ...item, reserved: item.reserved + 1 };
        }

        if (action === "release" && item.reserved > 0) {
          return { ...item, reserved: item.reserved - 1 };
        }

        return item;
      })
    );
  };

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-sm font-medium text-accent">
            WORKSPACE / INVENTORY
          </div>
          <h1 className="mt-2 font-display text-3xl font-bold">
            Inventory management
          </h1>
          <p className="mt-2 text-text-secondary">
            Monitor campus resources, availability and reservations.
          </p>
        </div>
      </div>

      {/* Inventory statistics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Resource types", resources.length],
          ["Total quantity", totalQuantity],
          ["Available units", availableQuantity],
          ["Reserved units", totalReserved],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-2xl border border-ui-border bg-ui-surface p-5"
          >
            <p className="text-sm text-text-secondary">{label}</p>
            <p className="mt-3 text-3xl font-bold">{value}</p>
          </div>
        ))}
      </div>

      {/* Search and filters */}
      <div className="rounded-2xl border border-ui-border bg-ui-surface p-5">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search resources, categories or owners..."
          className="w-full rounded-xl border border-ui-border bg-ui-subtle px-4 py-3 outline-none focus:border-ui-accent"
        />

        <div className="mt-4 flex flex-wrap gap-2">
          {["All", "Available", "Fully Reserved"].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`rounded-xl border px-4 py-2 text-sm font-medium ${statusFilter === status
                ? "border-ui-accent bg-ui-accent text-white"
                : "border-ui-border bg-ui-surface text-text-secondary"
                }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Inventory table */}
      <div className="overflow-hidden rounded-2xl border border-ui-border bg-ui-surface">
        <div className="border-b border-ui-border p-5">
          <h2 className="font-display text-lg font-bold">
            Campus inventory
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            {filteredResources.length} resource types displayed
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[750px] text-left text-sm">
            <thead className="bg-ui-subtle text-text-secondary">
              <tr>
                <th className="p-4">Resource</th>
                <th className="p-4">Category</th>
                <th className="p-4">Department</th>
                <th className="p-4">Quantity</th>
                <th className="p-4">Reserved</th>
                <th className="p-4">Available</th>
                <th className="p-4">Status</th>
                <th className="p-4">Actions</th>
              </tr>
            </thead>

            <tbody>
              {filteredResources.map((item) => {
                const available = item.quantity - item.reserved;
                const status = getStatus(item);

                return (
                  <tr
                    key={item.id}
                    className="border-t border-ui-border"
                  >
                    <td className="p-4 font-semibold">{item.name}</td>
                    <td className="p-4 text-text-secondary">
                      {item.category}
                    </td>
                    <td className="p-4 text-text-secondary">
                      {item.location}
                    </td>
                    <td className="p-4">{item.quantity}</td>
                    <td className="p-4">{item.reserved}</td>
                    <td className="p-4 font-semibold">{available}</td>
                    <td className="p-4">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${status === "Available"
                          ? "bg-ui-success-bg text-ui-success-text"
                          : status === "Fully Reserved"
                            ? "bg-ui-warning-bg text-ui-warning-text"
                            : "bg-ui-accent-soft text-ui-accent"
                          }`}
                      >
                        {status}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <button
                          disabled={available === 0}
                          onClick={() => updateReservation(item.id, "reserve")}
                          className="rounded-lg bg-ui-accent px-3 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          Reserve
                        </button>
                        <button
                          disabled={item.reserved === 0}
                          onClick={() => updateReservation(item.id, "release")}
                          className="rounded-lg border border-ui-border px-3 py-2 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          Release
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filteredResources.length === 0 && (
          <div className="p-10 text-center text-text-secondary">
            No inventory resources found.
          </div>
        )}
      </div>
    </div>
  );
}


function Transfers() {
  const [transfers, setTransfers] = useState([
    {
      id: "TR-1001",
      resource: "Engineering Mathematics",
      sender: "Rahul Sharma",
      recipient: "Aarav Kumar",
      department: "Computer Science",
      quantity: 1,
      date: "7 Nov 2026",
      status: "In Transit",
    },
    {
      id: "TR-1002",
      resource: "Dell Laptop Stand",
      sender: "Ananya R",
      recipient: "Sneha R",
      department: "Information Technology",
      quantity: 1,
      date: "6 Nov 2026",
      status: "Awaiting Receipt",
    },
    {
      id: "TR-1003",
      resource: "Chemistry Lab Kit",
      sender: "Arjun K",
      recipient: "Rahul S",
      department: "Biotechnology",
      quantity: 1,
      date: "5 Nov 2026",
      status: "Completed",
    },
    {
      id: "TR-1004",
      resource: "Data Structures Notes",
      sender: "Meera S",
      recipient: "Karan M",
      department: "Computer Science",
      quantity: 2,
      date: "4 Nov 2026",
      status: "Completed",
    },
  ]);

  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");

  const counts = {
    total: transfers.length,
    transit: transfers.filter((t) => t.status === "In Transit").length,
    awaiting: transfers.filter((t) => t.status === "Awaiting Receipt").length,
    completed: transfers.filter((t) => t.status === "Completed").length,
  };

  const filteredTransfers = transfers.filter((t) => {
    const matchesSearch =
      t.resource.toLowerCase().includes(search.toLowerCase()) ||
      t.sender.toLowerCase().includes(search.toLowerCase()) ||
      t.recipient.toLowerCase().includes(search.toLowerCase()) ||
      t.id.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      filter === "All" || t.status === filter;

    return matchesSearch && matchesFilter;
  });

  const confirmReceipt = (id) => {
    setTransfers((current) =>
      current.map((t) =>
        t.id === id && t.status === "Awaiting Receipt"
          ? { ...t, status: "Completed" }
          : t
      )
    );
  };

  const statusStyle = (status) => {
    if (status === "Completed") {
      return "bg-ui-success-bg text-ui-success-text";
    }

    if (status === "Awaiting Receipt") {
      return "bg-ui-warning-bg text-ui-warning-text";
    }

    return "bg-ui-accent-soft text-ui-accent";
  };

  return (
    <div className="space-y-7">
      {/* Page heading */}
      <div>
        <p className="text-sm font-medium text-ui-accent">
          WORKSPACE / TRANSFERS
        </p>
        <h1 className="mt-2 font-display text-3xl font-bold">
          Resource transfers
        </h1>
        <p className="mt-2 text-text-secondary">
          Track resource movements and confirm successful receipt.
        </p>
      </div>

      {/* Statistics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Total transfers", counts.total],
          ["In transit", counts.transit],
          ["Awaiting receipt", counts.awaiting],
          ["Completed", counts.completed],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-2xl border border-ui-border bg-ui-surface p-5"
          >
            <p className="text-sm text-text-secondary">{label}</p>
            <p className="mt-3 text-3xl font-bold">{value}</p>
          </div>
        ))}
      </div>

      {/* Search and filters */}
      <div className="rounded-2xl border border-ui-border bg-ui-surface p-5">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by transfer ID, resource or student..."
          className="w-full rounded-xl border border-ui-border bg-ui-subtle px-4 py-3 outline-none focus:border-ui-accent"
        />

        <div className="mt-4 flex flex-wrap gap-2">
          {[
            "All",
            "In Transit",
            "Awaiting Receipt",
            "Completed",
          ].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`rounded-xl border px-4 py-2 text-sm font-medium ${filter === status
                ? "border-ui-accent bg-ui-accent text-white"
                : "border-ui-border bg-ui-surface text-text-secondary"
                }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Transfer records */}
      <div className="overflow-hidden rounded-2xl border border-ui-border bg-ui-surface">
        <div className="border-b border-ui-border p-5">
          <h2 className="font-display text-lg font-bold">
            Transfer history
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            {filteredTransfers.length} transfers displayed
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-ui-subtle text-text-secondary">
              <tr>
                <th className="p-4">Transfer ID</th>
                <th className="p-4">Resource</th>
                <th className="p-4">Sender</th>
                <th className="p-4">Recipient</th>
                <th className="p-4">Quantity</th>
                <th className="p-4">Date</th>
                <th className="p-4">Status</th>
                <th className="p-4">Action</th>
              </tr>
            </thead>

            <tbody>
              {filteredTransfers.map((t) => (
                <tr key={t.id} className="border-t border-ui-border">
                  <td className="p-4 font-semibold">{t.id}</td>
                  <td className="p-4 font-medium">{t.resource}</td>
                  <td className="p-4 text-text-secondary">{t.sender}</td>
                  <td className="p-4 text-text-secondary">{t.recipient}</td>
                  <td className="p-4">{t.quantity}</td>
                  <td className="p-4 text-text-secondary">{t.date}</td>
                  <td className="p-4">
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${statusStyle(t.status)}`}
                    >
                      {t.status}
                    </span>
                  </td>
                  <td className="p-4">
                    {t.status === "Awaiting Receipt" ? (
                      <button
                        onClick={() => confirmReceipt(t.id)}
                        className="whitespace-nowrap rounded-lg bg-ui-success px-3 py-2 text-xs font-semibold text-white"
                      >
                        Confirm receipt
                      </button>
                    ) : (
                      <span className="text-xs text-text-muted">
                        {t.status === "Completed"
                          ? "Received"
                          : "In progress"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredTransfers.length === 0 && (
          <div className="p-10 text-center text-text-secondary">
            No transfers found.
          </div>
        )}
      </div>
    </div>
  );
}


function Analytics() {
  const [period, setPeriod] = useState("This month");

  const data = {
    "This week": {
      resources: 18,
      donations: 8,
      exchanges: 6,
      enquiries: 4,
      requests: 12,
      completed: 9,
      trend: [35, 55, 40, 75, 60, 90, 70],
    },
    "This month": {
      resources: 128,
      donations: 54,
      exchanges: 46,
      enquiries: 28,
      requests: 86,
      completed: 72,
      trend: [35, 55, 45, 70, 60, 85, 75, 95, 65, 80, 90, 100],
    },
    "This year": {
      resources: 842,
      donations: 356,
      exchanges: 301,
      enquiries: 185,
      requests: 624,
      completed: 518,
      trend: [30, 45, 40, 60, 55, 75, 65, 90, 80, 100, 85, 95],
    },
  };

  const stats = data[period];

  const categories = [
    { name: "Books & study material", count: 42 },
    { name: "Electronics", count: 28 },
    { name: "Lab equipment", count: 22 },
    { name: "Stationery", count: 18 },
    { name: "Others", count: 18 },
  ];

  const totalCategoryCount = categories.reduce(
    (sum, item) => sum + item.count,
    0
  );

  const maxTrend = Math.max(...stats.trend);

  const metrics = [
    {
      label: "Total resources",
      value: stats.resources,
      description: "Resources listed",
      color: "text-ui-accent",
    },
    {
      label: "Donations",
      value: stats.donations,
      description: "Resources shared for free",
      color: "text-ui-success-text",
    },
    {
      label: "Exchanges",
      value: stats.exchanges,
      description: "Successful resource exchanges",
      color: "text-ui-accent",
    },
    {
      label: "Purchase enquiries",
      value: stats.enquiries,
      description: "Enquiries submitted",
      color: "text-ui-warning-text",
    },
  ];

  return (
    <div className="space-y-7">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-ui-accent">
            WORKSPACE / ANALYTICS
          </p>
          <h1 className="mt-2 font-display text-3xl font-bold">
            Campus analytics
          </h1>
          <p className="mt-2 text-text-secondary">
            Understand resource sharing and campus activity.
          </p>
        </div>

        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="rounded-xl border border-ui-border bg-ui-surface px-4 py-3"
        >
          <option>This week</option>
          <option>This month</option>
          <option>This year</option>
        </select>
      </div>

      {/* Main metrics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className="rounded-2xl border border-ui-border bg-ui-surface p-5"
          >
            <p className="text-sm text-text-secondary">
              {metric.label}
            </p>
            <p className={`mt-3 text-3xl font-bold ${metric.color}`}>
              {metric.value}
            </p>
            <p className="mt-2 text-xs text-text-muted">
              {metric.description}
            </p>
          </div>
        ))}
      </div>

      {/* Activity summary */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-ui-border bg-ui-surface p-6">
          <h2 className="font-display text-lg font-bold">
            Request performance
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Requests submitted and completed
          </p>

          <div className="mt-6 flex items-end gap-8">
            <div>
              <p className="text-3xl font-bold">{stats.requests}</p>
              <p className="mt-1 text-xs text-text-muted">
                Total requests
              </p>
            </div>
            <div>
              <p className="text-3xl font-bold text-ui-success-text">
                {stats.completed}
              </p>
              <p className="mt-1 text-xs text-text-muted">
                Completed
              </p>
            </div>
          </div>

          <div className="mt-6 h-3 overflow-hidden rounded-full bg-ui-subtle">
            <div
              className="h-full rounded-full bg-ui-success"
              style={{
                width: `${stats.requests > 0
                  ? (stats.completed / stats.requests) * 100
                  : 0}%`,
              }}
            />
          </div>

          <p className="mt-2 text-sm text-text-secondary">
            {Math.round(
              (stats.completed / stats.requests) * 100
            )}% completion rate
          </p>
        </div>

        <div className="rounded-2xl border border-ui-border bg-ui-surface p-6">
          <h2 className="font-display text-lg font-bold">
            Transfer performance
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Resource transfers completed
          </p>

          <p className="mt-6 text-3xl font-bold">
            {Math.round(stats.completed * 0.8)}
          </p>

          <p className="mt-1 text-sm text-text-secondary">
            Estimated completed transfers
          </p>

          <div className="mt-6 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-ui-success" />
            <span className="text-sm text-text-secondary">
              Completion activity
            </span>
          </div>
        </div>
      </div>

      {/* Resource activity chart */}
      <div className="rounded-2xl border border-ui-border bg-ui-surface p-6">
        <div>
          <h2 className="font-display text-lg font-bold">
            Resource activity trend
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Illustrative activity distribution for {period.toLowerCase()}
          </p>
        </div>

        <div className="mt-8 flex h-52 items-end gap-2 sm:gap-4">
          {stats.trend.map((value, index) => (
            <div
              key={index}
              className="flex h-full flex-1 flex-col justify-end"
            >
              <div
                className="w-full rounded-t-lg bg-ui-accent transition-all duration-300"
                style={{
                  height: `${(value / maxTrend) * 100}%`,
                  minHeight: "4px",
                }}
                title={`Activity: ${value}`}
              />
              <span className="mt-2 text-center text-xs text-text-muted">
                {index + 1}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Category breakdown */}
      <div className="rounded-2xl border border-ui-border bg-ui-surface p-6">
        <h2 className="font-display text-lg font-bold">
          Resource category distribution
        </h2>
        <p className="mt-1 text-sm text-text-secondary">
          Distribution of listed resources by category
        </p>

        <div className="mt-6 space-y-5">
          {categories.map((category) => {
            const percentage = Math.round(
              (category.count / totalCategoryCount) * 100
            );

            return (
              <div key={category.name}>
                <div className="mb-2 flex justify-between gap-3 text-sm">
                  <span className="font-medium">{category.name}</span>
                  <span className="text-text-secondary">
                    {category.count} · {percentage}%
                  </span>
                </div>

                <div className="h-2.5 overflow-hidden rounded-full bg-ui-subtle">
                  <div
                    className="h-full rounded-full bg-ui-accent"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <p className="text-xs text-text-muted">
        Demonstration analytics using sample data. Actual reports will
        be generated from database records after backend integration.
      </p>
    </div>
  );
}


function ModulePlaceholder({ page, onBack }) {
  const moduleDescriptions = {
    Marketplace: "Discover resources shared by your campus community.",
    "My Listings": "Create and manage your resource listings.",
    "My Requests": "Track requests and respond to incoming enquiries.",
    Inventory: "Manage available campus resources and reservations.",
    Transfers: "Manage resource transfers and receipt confirmations.",
    Analytics: "Understand resource sharing activity across campus.",
    Settings: "Manage your account and application preferences.",
    "Help & Support": "Find guidance for using CampusCycle.",
    "Sign out": "Authentication and sign-out will be connected in a later stage.",
  };

  return (
    <section className="mx-auto max-w-3xl py-12">
      <div className="rounded-2xl border border-ui-border bg-ui-surface p-8 sm:p-12">
        <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-ui-accent-soft text-ui-accent">
          <Package size={27} />
        </div>
        <p className="text-xs font-semibold tracking-wider text-ui-accent">
          CAMPUSCYCLE WORKSPACE
        </p>
        <h2 className="mt-3 font-display text-3xl font-bold">{page}</h2>
        <p className="mt-3 max-w-lg text-sm leading-6 text-ui-text-secondary">
          {moduleDescriptions[page] ||
            "This section will be implemented in the next development stage."}
        </p>
        <div className="mt-7 rounded-xl border border-ui-border bg-ui-subtle p-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Clock3 size={17} className="text-ui-warning" />
            Implementation pending
          </div>
          <p className="mt-2 text-xs leading-5 text-ui-text-muted">
            The application shell and dashboard are in place. This module
            will receive its actual functionality in a subsequent step.
          </p>
        </div>
        <button
          type="button"
          onClick={onBack}
          className="mt-7 inline-flex items-center gap-2 rounded-xl bg-ui-accent px-5 py-3 text-sm font-semibold text-white transition hover:bg-ui-accent-hover"
        >
          <ArrowRight size={16} className="rotate-180" />
          Back to overview
        </button>
      </div>
    </section>
  );
}

export default App;
