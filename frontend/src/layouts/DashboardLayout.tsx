import React, { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/AuthContext';
import { useMetricsWebSocket } from '../hooks/useMetricsWebSocket';
import { alertsApi } from '../services/api';
import { formatRelativeTime } from '../utils/format';

const NAV_ITEMS = [
  { to: '/', label: 'Overview', end: true, activeCls: 'bg-indigo-50 text-indigo-700 border-indigo-200', dot: 'bg-indigo-500' },
  { to: '/servers', label: 'Servers', end: false, activeCls: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: 'bg-emerald-500' },
  { to: '/monitoring', label: 'Monitoring', end: false, activeCls: 'bg-sky-50 text-sky-700 border-sky-200', dot: 'bg-sky-500' },
  { to: '/alerts', label: 'Alerts', end: false, activeCls: 'bg-rose-50 text-rose-700 border-rose-200', dot: 'bg-rose-500' },
  { to: '/logs', label: 'Logs', end: false, activeCls: 'bg-amber-50 text-amber-800 border-amber-200', dot: 'bg-amber-500' },
  { to: '/processes', label: 'Processes', end: false, activeCls: 'bg-violet-50 text-violet-700 border-violet-200', dot: 'bg-violet-500' },
  { to: '/settings', label: 'Settings', end: false, activeCls: 'bg-teal-50 text-teal-700 border-teal-200', dot: 'bg-teal-500' },
];

export const DashboardLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const { connectionState, lastEventAt, addListener } = useMetricsWebSocket();
  const navigate = useNavigate();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeAlertsCount, setActiveAlertsCount] = useState(0);

  useEffect(() => {
    let mounted = true;
    const fetchSummary = () => {
      alertsApi
        .summary()
        .then((s) => {
          if (mounted) setActiveAlertsCount(s.active + s.acknowledged);
        })
        .catch(() => {});
    };
    fetchSummary();
    const unsub = addListener((evt) => {
      if (evt.type === 'alert_event') {
        fetchSummary();
      }
    });
    return () => {
      mounted = false;
      unsub();
    };
  }, [addListener]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = searchTerm.trim();
    if (trimmed) {
      navigate(`/servers?search=${encodeURIComponent(trimmed)}`);
      setSearchTerm('');
    }
  };

  const wsBadge =
    connectionState === 'connected'
      ? { cls: 'text-emerald-700 bg-emerald-50 border-emerald-200', dot: 'bg-emerald-500', label: 'Live' }
      : connectionState === 'connecting'
        ? { cls: 'text-amber-800 bg-amber-50 border-amber-200', dot: 'bg-amber-500', label: 'Connecting' }
        : { cls: 'text-slate-600 bg-slate-100 border-slate-200', dot: 'bg-slate-400', label: 'Offline' };

  return (
    <div className="min-h-screen bg-[#F7F8FC] text-slate-900 flex">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-60 bg-white border-r border-slate-200 flex flex-col transition-transform duration-200 lg:static lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Multicolor top hairline */}
        <div className="h-1 w-full bg-gradient-to-r from-rose-400 via-amber-400 via-emerald-400 to-indigo-500" />

        <div className="h-16 px-5 border-b border-slate-100 flex items-center justify-between">
          <Link to="/" className="block">
            <span className="text-lg font-extrabold tracking-tight text-slate-900 block leading-none">
              Sentinel<span className="text-indigo-600">Ops</span>
            </span>
            <span className="text-[10px] font-mono text-slate-500 tracking-wider uppercase mt-1 block">
              Linux Observability
            </span>
          </Link>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="lg:hidden text-xs font-semibold text-slate-500 hover:text-slate-800 px-2 py-1"
          >
            Close
          </button>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, end, activeCls, dot }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium border transition-colors ${
                  isActive
                    ? activeCls
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 border-transparent'
                }`
              }
            >
              <span className="flex items-center gap-2.5">
                <span className={`w-2 h-2 rounded-full ${dot}`} />
                {label}
              </span>
              {label === 'Alerts' && activeAlertsCount > 0 && (
                <span className="px-2 py-0.5 text-[11px] font-mono font-bold rounded-full bg-rose-100 text-rose-700">
                  {activeAlertsCount}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-100 text-[11px] text-slate-400 font-mono flex items-center justify-between">
          <span>SentinelOps v1.0</span>
          <span className="text-emerald-600 font-semibold">UTC</span>
        </div>
      </aside>

      {/* Main Column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-16 bg-white/90 backdrop-blur border-b border-slate-200/90 px-4 lg:px-6 flex items-center justify-between gap-4 sticky top-0 z-30">
          <div className="flex items-center gap-3 flex-1 max-w-md">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="lg:hidden px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Menu
            </button>
            <form onSubmit={handleSearchSubmit} className="flex-1">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search servers by hostname, IP, OS..."
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
              />
            </form>
          </div>

          <div className="flex items-center gap-3">
            {/* WebSocket Status Pill */}
            <div
              className={`hidden sm:inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium ${wsBadge.cls}`}
              title={lastEventAt ? `Last update: ${new Date(lastEventAt).toLocaleTimeString()}` : 'WebSocket telemetry'}
            >
              <span className={`w-2 h-2 rounded-full ${wsBadge.dot}`} />
              <span>{wsBadge.label}</span>
              {lastEventAt && (
                <span className="text-[11px] font-mono opacity-75 hidden md:inline">
                  · {formatRelativeTime(lastEventAt)}
                </span>
              )}
            </div>

            {/* Active Alerts shortcut */}
            <Link
              to="/alerts"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-rose-200 bg-rose-50/70 hover:bg-rose-100/80 text-xs font-medium text-rose-700 transition-colors"
            >
              <span>Alerts</span>
              <span className="font-mono font-bold">{activeAlertsCount}</span>
            </Link>

            {/* User Profile & Sign Out */}
            <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
              <div className="text-right hidden sm:block">
                <p className="text-xs font-semibold text-slate-800 leading-none">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-[10px] font-mono uppercase text-indigo-600 mt-0.5 font-semibold">
                  {user?.role}
                </p>
              </div>
              <button
                type="button"
                onClick={logout}
                className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:text-rose-700 hover:border-rose-200 hover:bg-rose-50 transition-colors"
              >
                Sign out
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-6 max-w-[1600px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
