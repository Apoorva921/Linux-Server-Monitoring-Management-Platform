import React, { useCallback, useEffect, useState } from 'react';
import { ErrorBanner, LoadingSpinner } from '../components/Feedback';
import { MetricCard } from '../components/MetricCard';
import { DemoBadge, SeverityBadge } from '../components/StatusBadge';
import { useMetricsWebSocket } from '../hooks/useMetricsWebSocket';
import { alertsApi, serversApi } from '../services/api';
import type { Alert, AlertSummary, Server } from '../types';
import { extractErrorMessage, formatDateTime } from '../utils/format';

export const AlertsPage: React.FC = () => {
  const { addListener } = useMetricsWebSocket();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [servers, setServers] = useState<Server[]>([]);
  const [severity, setSeverity] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [serverId, setServerId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const loadAlerts = useCallback(async () => {
    try {
      const [listRes, sumRes] = await Promise.all([
        alertsApi.list({
          severity: severity || undefined,
          status: statusFilter || undefined,
          server_id: serverId || undefined,
          page_size: 100,
        }),
        alertsApi.summary(),
      ]);
      setAlerts(listRes.items);
      setSummary(sumRes);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load alerts.'));
    } finally {
      setLoading(false);
    }
  }, [severity, statusFilter, serverId]);

  useEffect(() => {
    serversApi
      .list({ page_size: 100 })
      .then((res) => setServers(res.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  useEffect(() => {
    return addListener((evt) => {
      if (evt.type === 'alert_event') {
        loadAlerts();
      }
    });
  }, [addListener, loadAlerts]);

  const handleAcknowledge = async (id: string) => {
    setBusyId(id);
    try {
      const updated = await alertsApi.acknowledge(id);
      setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
      const sum = await alertsApi.summary();
      setSummary(sum);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to acknowledge alert.'));
    } finally {
      setBusyId(null);
    }
  };

  const handleResolve = async (id: string) => {
    setBusyId(id);
    try {
      const updated = await alertsApi.resolve(id);
      setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
      const sum = await alertsApi.summary();
      setSummary(sum);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to resolve alert.'));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Alert Management</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Threshold violations with duplicate suppression, cooldown windows, and automatic recovery
        </p>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadAlerts} />}

      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Active Critical"
            value={summary.critical_active}
            subtitle="Immediate attention required"
            accent="rose"
          />
          <MetricCard
            label="Active Warning"
            value={summary.warning_active}
            subtitle="Elevated resource consumption"
            accent="amber"
          />
          <MetricCard
            label="Acknowledged"
            value={summary.acknowledged}
            subtitle="Under investigation"
            accent="sky"
          />
          <MetricCard
            label="Resolved"
            value={summary.resolved}
            subtitle={`${summary.total} total historical alerts`}
            accent="emerald"
          />
        </div>
      )}

      {/* Filters */}
      <div className="panel p-4 flex flex-wrap items-center gap-3">
        <select
          aria-label="Filter by severity"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
        </select>

        <select
          aria-label="Filter by status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>

        <select
          aria-label="Filter by server"
          value={serverId}
          onChange={(e) => setServerId(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800"
        >
          <option value="">All Servers</option>
          {servers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.display_name}
            </option>
          ))}
        </select>
      </div>

      {/* Alert List */}
      <div className="panel overflow-hidden">
        {loading ? (
          <LoadingSpinner label="Loading alerts..." />
        ) : alerts.length === 0 ? (
          <div className="p-10 text-center text-sm text-slate-500">
            No alerts match the current filters.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="p-4 sm:px-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/70"
              >
                <div className="min-w-0 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <SeverityBadge severity={alert.severity} />
                    <span className="text-sm font-semibold text-slate-900">{alert.title}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-semibold border ${
                        alert.status === 'active'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : alert.status === 'acknowledged'
                            ? 'bg-sky-50 text-sky-700 border-sky-200'
                            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      }`}
                    >
                      {alert.status}
                    </span>
                    {alert.is_demo && <DemoBadge />}
                  </div>
                  <p className="text-xs text-slate-700">{alert.description}</p>
                  <p className="text-[11px] font-mono text-slate-500">
                    Server: {alert.server_name} · Metric: {alert.metric_type} · Triggered:{' '}
                    {formatDateTime(alert.created_at)}
                    {alert.resolved_at && ` · Resolved: ${formatDateTime(alert.resolved_at)}`}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {alert.status === 'active' && (
                    <button
                      type="button"
                      disabled={busyId === alert.id}
                      onClick={() => handleAcknowledge(alert.id)}
                      className="px-3 py-1.5 rounded-lg bg-sky-50 hover:bg-sky-100 border border-sky-200 text-sky-700 text-xs font-semibold disabled:opacity-50"
                    >
                      Acknowledge
                    </button>
                  )}
                  {alert.status !== 'resolved' && (
                    <button
                      type="button"
                      disabled={busyId === alert.id}
                      onClick={() => handleResolve(alert.id)}
                      className="px-3 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-700 text-xs font-semibold disabled:opacity-50"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
