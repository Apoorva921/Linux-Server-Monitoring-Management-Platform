import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ErrorBanner, LoadingSpinner } from '../components/Feedback';
import { MetricCard } from '../components/MetricCard';
import { DemoBadge, SeverityBadge, StatusBadge } from '../components/StatusBadge';
import { NetworkThroughputChart, ResourceAreaChart } from '../components/TelemetryCharts';
import { useMetricsWebSocket } from '../hooks/useMetricsWebSocket';
import { dashboardApi } from '../services/api';
import type { DashboardSummary, FleetTrendPoint, ServerStatus } from '../types';
import { extractErrorMessage, formatBps, formatRelativeTime } from '../utils/format';

export const OverviewPage: React.FC = () => {
  const { addListener } = useMetricsWebSocket();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    try {
      const data = await dashboardApi.getSummary();
      setSummary(data);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load fleet summary.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSummary();
    const timer = window.setInterval(loadSummary, 15000);
    return () => window.clearInterval(timer);
  }, [loadSummary]);

  useEffect(() => {
    return addListener((evt) => {
      if (evt.type === 'metric_update' && evt.server_id && evt.data) {
        const d = evt.data;
        setSummary((prev) => {
          if (!prev) return prev;
          const updatedServers = prev.servers.map((srv) => {
            if (srv.id !== evt.server_id) return srv;
            return {
              ...srv,
              status: String(d.status || srv.status) as ServerStatus,
              health_score: Number(d.health_score ?? srv.health_score),
              uptime_seconds: Number(d.uptime_seconds ?? srv.uptime_seconds),
              last_heartbeat: String(d.timestamp || new Date().toISOString()),
              latest_metric: {
                ...(srv.latest_metric || {
                  net_bytes_sent: 0,
                  net_bytes_recv: 0,
                  net_packets_sent: 0,
                  net_packets_recv: 0,
                  net_interface: 'eth0',
                }),
                timestamp: String(d.timestamp),
                cpu_percent: Number(d.cpu_percent ?? 0),
                memory_percent: Number(d.memory_percent ?? 0),
                memory_used_mb: Number(d.memory_used_mb ?? 0),
                memory_total_mb: Number(d.memory_total_mb ?? 0),
                disk_percent: Number(d.disk_percent ?? 0),
                disk_used_gb: Number(d.disk_used_gb ?? 0),
                disk_total_gb: Number(d.disk_total_gb ?? 0),
                net_upload_bps: Number(d.net_upload_bps ?? 0),
                net_download_bps: Number(d.net_download_bps ?? 0),
                load_1m: Number(d.load_1m ?? 0),
                load_5m: Number(d.load_5m ?? 0),
                load_15m: Number(d.load_15m ?? 0),
                uptime_seconds: Number(d.uptime_seconds ?? 0),
                process_count: Number(d.process_count ?? 0),
              },
            };
          });

          const onlineWithMetrics = updatedServers
            .filter((s) => s.status !== 'offline' && s.latest_metric)
            .map((s) => s.latest_metric!);

          const avgCpu = onlineWithMetrics.length
            ? Number((onlineWithMetrics.reduce((a, m) => a + m.cpu_percent, 0) / onlineWithMetrics.length).toFixed(2))
            : 0;
          const avgMem = onlineWithMetrics.length
            ? Number((onlineWithMetrics.reduce((a, m) => a + m.memory_percent, 0) / onlineWithMetrics.length).toFixed(2))
            : 0;
          const avgDisk = onlineWithMetrics.length
            ? Number((onlineWithMetrics.reduce((a, m) => a + m.disk_percent, 0) / onlineWithMetrics.length).toFixed(2))
            : 0;
          const totalUp = onlineWithMetrics.reduce((a, m) => a + m.net_upload_bps, 0);
          const totalDown = onlineWithMetrics.reduce((a, m) => a + m.net_download_bps, 0);

          const nextPoint: FleetTrendPoint = {
            timestamp: String(d.timestamp || new Date().toISOString()),
            avg_cpu_percent: avgCpu,
            avg_memory_percent: avgMem,
            avg_disk_percent: avgDisk,
            total_upload_bps: totalUp,
            total_download_bps: totalDown,
          };

          const offlineCount = updatedServers.filter((s) => s.status === 'offline').length;
          return {
            ...prev,
            servers: updatedServers,
            online_servers: updatedServers.length - offlineCount,
            offline_servers: offlineCount,
            healthy_servers: updatedServers.filter((s) => s.status === 'healthy').length,
            warning_servers: updatedServers.filter((s) => s.status === 'warning').length,
            critical_servers: updatedServers.filter((s) => s.status === 'critical').length,
            avg_cpu_percent: avgCpu,
            avg_memory_percent: avgMem,
            avg_disk_percent: avgDisk,
            total_net_upload_bps: totalUp,
            total_net_download_bps: totalDown,
            trend_series: [...prev.trend_series.slice(-59), nextPoint],
          };
        });
      } else if (evt.type === 'alert_event' || evt.type === 'server_status') {
        loadSummary();
      }
    });
  }, [addListener, loadSummary]);

  if (loading) return <LoadingSpinner label="Loading fleet telemetry..." />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Infrastructure Overview</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time Linux server health, resource utilization, and active alerts
          </p>
        </div>
        {summary?.has_demo_data && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-sky-50 border border-sky-200 text-xs text-sky-900">
            <DemoBadge />
            <span>
              {summary.has_real_data
                ? 'Fleet contains both real hosts and clearly labeled simulated demo hosts.'
                : 'Displaying simulated DEMO DATA from SentinelOps Demo Mode.'}
            </span>
          </div>
        )}
      </div>

      {error && <ErrorBanner message={error} onRetry={loadSummary} />}

      {summary && (
        <>
          {/* Pastel Multicolor Metric Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-6 gap-4">
            <MetricCard
              label="Servers Online"
              value={`${summary.online_servers} / ${summary.total_servers}`}
              subtitle={`${summary.offline_servers} offline · ${summary.warning_servers} warning`}
              accent="emerald"
            />
            <MetricCard
              label="Active Alerts"
              value={summary.active_alerts}
              subtitle={`${summary.critical_alerts} critical · ${summary.warning_alerts} warning`}
              accent={summary.critical_alerts > 0 ? 'rose' : summary.warning_alerts > 0 ? 'amber' : 'emerald'}
            />
            <MetricCard
              label="Fleet Avg CPU"
              value={`${summary.avg_cpu_percent.toFixed(1)}%`}
              subtitle="Across online hosts"
              accent="rose"
              percent={summary.avg_cpu_percent}
            />
            <MetricCard
              label="Fleet Avg Memory"
              value={`${summary.avg_memory_percent.toFixed(1)}%`}
              subtitle="RAM utilization"
              accent="indigo"
              percent={summary.avg_memory_percent}
            />
            <MetricCard
              label="Fleet Avg Disk"
              value={`${summary.avg_disk_percent.toFixed(1)}%`}
              subtitle="Monitored volumes"
              accent="amber"
              percent={summary.avg_disk_percent}
            />
            <MetricCard
              label="Network I/O"
              value={formatBps(summary.total_net_download_bps)}
              subtitle={`Upload: ${formatBps(summary.total_net_upload_bps)}`}
              accent="teal"
            />
          </div>

          {/* Trend Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ResourceAreaChart
              title="Fleet CPU Utilization"
              subtitle="Average CPU usage over time"
              data={summary.trend_series as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
              dataKey="avg_cpu_percent"
              color="#f43f5e"
            />
            <ResourceAreaChart
              title="Fleet Memory Utilization"
              subtitle="Average RAM usage over time"
              data={summary.trend_series as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
              dataKey="avg_memory_percent"
              color="#7c3aed"
            />
            <NetworkThroughputChart
              title="Fleet Network Traffic"
              subtitle="Aggregate live upload & download throughput"
              data={summary.trend_series as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
              uploadKey="total_upload_bps"
              downloadKey="total_download_bps"
            />
          </div>

          {/* Server Health Overview */}
          <div className="panel overflow-hidden">
            <div className="panel-header">
              <h2 className="text-sm font-semibold text-slate-900">Server Health Overview</h2>
              <Link
                to="/servers"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
              >
                Manage Servers &rarr;
              </Link>
            </div>
            {summary.servers.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">
                No servers registered yet. Go to{' '}
                <Link to="/servers" className="text-indigo-600 font-semibold underline">
                  Servers
                </Link>{' '}
                to register a Linux monitoring agent or launch Demo Mode.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-100 bg-slate-50/80">
                    <tr>
                      <th className="px-5 py-3">Host</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Health</th>
                      <th className="px-4 py-3">CPU</th>
                      <th className="px-4 py-3">Memory</th>
                      <th className="px-4 py-3">Disk</th>
                      <th className="px-4 py-3">Last Heartbeat</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {summary.servers.map((srv) => (
                      <tr key={srv.id} className="hover:bg-indigo-50/30 transition-colors">
                        <td className="px-5 py-3">
                          <Link
                            to={`/servers/${srv.id}`}
                            className="font-semibold text-slate-900 hover:text-indigo-600 flex items-center gap-2"
                          >
                            <span>{srv.display_name}</span>
                            {srv.is_demo && <DemoBadge />}
                          </Link>
                          <p className="text-xs font-mono text-slate-500">
                            {srv.ip_address} · {srv.os_name} {srv.os_version}
                          </p>
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={srv.status} />
                        </td>
                        <td className="px-4 py-3 font-mono font-bold text-slate-800">
                          {srv.health_score.toFixed(0)}/100
                        </td>
                        <td className="px-4 py-3 font-mono text-xs font-semibold text-rose-700">
                          {srv.latest_metric ? `${srv.latest_metric.cpu_percent.toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs font-semibold text-violet-700">
                          {srv.latest_metric ? `${srv.latest_metric.memory_percent.toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs font-semibold text-amber-700">
                          {srv.latest_metric ? `${srv.latest_metric.disk_percent.toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-500 font-mono">
                          {formatRelativeTime(srv.last_heartbeat)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Recent Alerts & Recent System Events */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="panel overflow-hidden">
              <div className="panel-header">
                <h2 className="text-sm font-semibold text-slate-900">Recent Alerts</h2>
                <Link to="/alerts" className="text-xs font-semibold text-rose-600 hover:text-rose-800">
                  View all &rarr;
                </Link>
              </div>
              <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
                {summary.recent_alerts.length === 0 ? (
                  <p className="p-6 text-xs text-slate-400 text-center">No threshold alerts recorded.</p>
                ) : (
                  summary.recent_alerts.map((alert) => (
                    <div key={alert.id} className="px-5 py-3 flex items-start justify-between gap-3 hover:bg-slate-50">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <SeverityBadge severity={alert.severity} />
                          <span className="text-xs font-semibold text-slate-800 truncate">{alert.title}</span>
                          {alert.is_demo && <DemoBadge />}
                        </div>
                        <p className="text-xs text-slate-600 mt-1 line-clamp-2">{alert.description}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <span className="text-[11px] font-mono uppercase text-slate-600 block">
                          {alert.status}
                        </span>
                        <span className="text-[11px] font-mono text-slate-400">
                          {formatRelativeTime(alert.created_at)}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="panel overflow-hidden">
              <div className="panel-header">
                <h2 className="text-sm font-semibold text-slate-900">Recent System Events</h2>
                <Link to="/logs" className="text-xs font-semibold text-amber-700 hover:text-amber-900">
                  Open Log Explorer &rarr;
                </Link>
              </div>
              <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto font-mono text-xs">
                {summary.recent_logs.length === 0 ? (
                  <p className="p-6 text-slate-400 text-center font-sans">No system logs ingested yet.</p>
                ) : (
                  summary.recent_logs.map((log) => (
                    <div key={log.id} className="px-5 py-2.5 flex items-start gap-2.5 hover:bg-slate-50">
                      <SeverityBadge severity={log.severity} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 text-[11px] text-slate-500">
                          <span className="text-indigo-700 font-semibold">{log.server_name}</span>
                          <span>·</span>
                          <span>{log.source}</span>
                          <span>·</span>
                          <span>{formatRelativeTime(log.timestamp)}</span>
                        </div>
                        <p className="text-slate-700 mt-0.5 break-words">{log.message}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
