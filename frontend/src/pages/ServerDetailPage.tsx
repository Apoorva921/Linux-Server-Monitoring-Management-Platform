import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ErrorBanner, LoadingSpinner } from '../components/Feedback';
import { HealthScorePanel } from '../components/HealthScorePanel';
import { MetricCard } from '../components/MetricCard';
import { DemoBadge, SeverityBadge, StatusBadge } from '../components/StatusBadge';
import { NetworkThroughputChart, ResourceAreaChart } from '../components/TelemetryCharts';
import { useMetricsWebSocket } from '../hooks/useMetricsWebSocket';
import { logsApi, serversApi } from '../services/api';
import type { ProcessInfo, Server, ServerMetric, ServerStatus, SystemLog } from '../types';
import {
  extractErrorMessage,
  formatBps,
  formatBytes,
  formatDateTime,
  formatRelativeTime,
  formatUptime,
} from '../utils/format';

type RangeKey = '15m' | '1h' | '6h' | '24h' | '7d';

export const ServerDetailPage: React.FC = () => {
  const { serverId } = useParams<{ serverId: string }>();
  const { addListener, subscribeTopic, unsubscribeTopic } = useMetricsWebSocket();

  const [server, setServer] = useState<Server | null>(null);
  const [history, setHistory] = useState<ServerMetric[]>([]);
  const [processes, setProcesses] = useState<ProcessInfo[]>([]);
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [range, setRange] = useState<RangeKey>('1h');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    if (!serverId) return;
    try {
      const [srv, hist, procs, logRes] = await Promise.all([
        serversApi.get(serverId),
        serversApi.getMetricsHistory(serverId, range, 200),
        serversApi.getProcesses(serverId, { sort_by: 'cpu_percent', order: 'desc' }),
        logsApi.search({ server_id: serverId, page_size: 25 }),
      ]);
      setServer(srv);
      setHistory(hist);
      setProcesses(procs.processes);
      setLogs(logRes.items);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load server telemetry.'));
    } finally {
      setLoading(false);
    }
  }, [serverId, range]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!serverId) return;
    subscribeTopic(serverId);
    const unsub = addListener((evt) => {
      if (evt.type === 'metric_update' && evt.server_id === serverId && evt.data) {
        const d = evt.data;
        const point: ServerMetric = {
          id: Date.now(),
          server_id: serverId,
          timestamp: String(d.timestamp || new Date().toISOString()),
          cpu_percent: Number(d.cpu_percent ?? 0),
          cpu_user: 0,
          cpu_system: 0,
          cpu_iowait: 0,
          memory_percent: Number(d.memory_percent ?? 0),
          memory_used_mb: Number(d.memory_used_mb ?? 0),
          memory_available_mb: 0,
          memory_total_mb: Number(d.memory_total_mb ?? 0),
          swap_percent: 0,
          disk_percent: Number(d.disk_percent ?? 0),
          disk_used_gb: Number(d.disk_used_gb ?? 0),
          disk_total_gb: Number(d.disk_total_gb ?? 0),
          disk_partitions: [],
          net_bytes_sent: Number(d.net_bytes_sent ?? 0),
          net_bytes_recv: Number(d.net_bytes_recv ?? 0),
          net_packets_sent: 0,
          net_packets_recv: 0,
          net_interface: 'eth0',
          net_upload_bps: Number(d.net_upload_bps ?? 0),
          net_download_bps: Number(d.net_download_bps ?? 0),
          load_1m: Number(d.load_1m ?? 0),
          load_5m: Number(d.load_5m ?? 0),
          load_15m: Number(d.load_15m ?? 0),
          uptime_seconds: Number(d.uptime_seconds ?? 0),
          process_count: Number(d.process_count ?? 0),
          top_processes: [],
          is_demo: Boolean(evt.is_demo),
        };
        setHistory((prev) => [...prev.slice(-199), point]);
        setServer((prev) =>
          prev
            ? {
                ...prev,
                status: String(d.status || prev.status) as ServerStatus,
                health_score: Number(d.health_score ?? prev.health_score),
                health_explanation: (d.health_explanation as Server['health_explanation']) || prev.health_explanation,
                uptime_seconds: point.uptime_seconds,
                load_avg_1m: point.load_1m,
                load_avg_5m: point.load_5m,
                load_avg_15m: point.load_15m,
                last_heartbeat: point.timestamp,
                latest_metric: point,
              }
            : prev,
        );
      }
    });
    return () => {
      unsub();
      unsubscribeTopic(serverId);
    };
  }, [serverId, addListener, subscribeTopic, unsubscribeTopic]);

  if (loading) return <LoadingSpinner label="Loading host telemetry..." />;
  if (!server) return <ErrorBanner message={error || 'Server not found.'} />;

  const latest = history[history.length - 1] || server.latest_metric;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/servers" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 mb-1.5 inline-block">
            &larr; Back to Servers
          </Link>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-slate-900">{server.display_name}</h1>
            <StatusBadge status={server.status} />
            {server.is_demo && <DemoBadge />}
          </div>
          <p className="text-xs font-mono text-slate-500 mt-1">
            {server.hostname} · {server.ip_address} · {server.os_name} {server.os_version} ({server.kernel_version},{' '}
            {server.architecture}) · {server.cpu_cores} vCPU · Agent v{server.agent_version}
          </p>
        </div>

        <div className="flex items-center gap-1 p-1 rounded-lg bg-white border border-slate-200">
          {(['15m', '1h', '6h', '24h', '7d'] as RangeKey[]).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRange(r)}
              className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold transition-colors ${
                range === r ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadAll} />}

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          label="CPU Usage"
          value={latest ? `${latest.cpu_percent.toFixed(1)}%` : '—'}
          subtitle={`Load: ${server.load_avg_1m.toFixed(2)} / ${server.load_avg_5m.toFixed(2)} / ${server.load_avg_15m.toFixed(2)}`}
          accent="rose"
          percent={latest?.cpu_percent}
        />
        <MetricCard
          label="Memory"
          value={latest ? `${latest.memory_percent.toFixed(1)}%` : '—'}
          subtitle={
            latest
              ? `${(latest.memory_used_mb / 1024).toFixed(1)} / ${(latest.memory_total_mb / 1024).toFixed(1)} GB`
              : '—'
          }
          accent="indigo"
          percent={latest?.memory_percent}
        />
        <MetricCard
          label="Disk"
          value={latest ? `${latest.disk_percent.toFixed(1)}%` : '—'}
          subtitle={latest ? `${latest.disk_used_gb.toFixed(1)} / ${latest.disk_total_gb.toFixed(1)} GB` : '—'}
          accent="amber"
          percent={latest?.disk_percent}
        />
        <MetricCard
          label="Network Rate"
          value={latest ? formatBps(latest.net_download_bps) : '—'}
          subtitle={latest ? `Out: ${formatBps(latest.net_upload_bps)} (${latest.net_interface})` : '—'}
          accent="teal"
        />
        <MetricCard
          label="Uptime"
          value={formatUptime(server.uptime_seconds)}
          subtitle={`Heartbeat: ${formatRelativeTime(server.last_heartbeat)}`}
          accent="emerald"
        />
      </div>

      <HealthScorePanel
        score={server.health_score}
        status={server.status}
        explanation={server.health_explanation}
      />

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ResourceAreaChart
          title="CPU Utilization"
          subtitle="Percentage of CPU time across all cores"
          data={history as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
          dataKey="cpu_percent"
          color="#f43f5e"
        />
        <ResourceAreaChart
          title="Memory Utilization"
          subtitle="RAM allocation percentage"
          data={history as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
          dataKey="memory_percent"
          color="#7c3aed"
        />
        <ResourceAreaChart
          title="Disk Utilization"
          subtitle="Aggregate monitored filesystem usage"
          data={history as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
          dataKey="disk_percent"
          color="#d97706"
        />
        <NetworkThroughputChart
          title="Network Throughput (Live Rate)"
          subtitle="Computed from counter deltas per interval (distinct from cumulative totals below)"
          data={history as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
          uploadKey="net_upload_bps"
          downloadKey="net_download_bps"
        />
      </div>

      {latest && (
        <div className="panel p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">
            Cumulative Network Counters (Since Host Boot · Interface: {latest.net_interface})
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-xs">
            <div className="p-3.5 rounded-xl bg-teal-50/70 border border-teal-200/80">
              <p className="text-teal-800">Total Bytes Sent</p>
              <p className="text-base font-bold text-teal-900 mt-1">{formatBytes(latest.net_bytes_sent)}</p>
            </div>
            <div className="p-3.5 rounded-xl bg-sky-50/70 border border-sky-200/80">
              <p className="text-sky-800">Total Bytes Received</p>
              <p className="text-base font-bold text-sky-900 mt-1">{formatBytes(latest.net_bytes_recv)}</p>
            </div>
            <div className="p-3.5 rounded-xl bg-violet-50/70 border border-violet-200/80">
              <p className="text-violet-800">Packets Sent</p>
              <p className="text-base font-bold text-violet-900 mt-1">
                {latest.net_packets_sent.toLocaleString()}
              </p>
            </div>
            <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200/80">
              <p className="text-amber-800">Packets Received</p>
              <p className="text-base font-bold text-amber-900 mt-1">
                {latest.net_packets_recv.toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Running Processes & Server Logs */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="panel overflow-hidden">
          <div className="panel-header">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Top Running Processes</h3>
              <p className="text-xs text-slate-500">Read-only snapshot (termination disabled)</p>
            </div>
            <Link to={`/processes?server_id=${server.id}`} className="text-xs font-semibold text-violet-700 hover:text-violet-900">
              Full explorer &rarr;
            </Link>
          </div>
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-left text-xs font-mono">
              <thead className="text-slate-500 border-b border-slate-100 bg-slate-50/80">
                <tr>
                  <th className="px-4 py-2.5">PID</th>
                  <th className="px-4 py-2.5">Process</th>
                  <th className="px-4 py-2.5">User</th>
                  <th className="px-4 py-2.5 text-right">CPU %</th>
                  <th className="px-4 py-2.5 text-right">MEM %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {processes.slice(0, 12).map((p) => (
                  <tr key={p.pid} className="hover:bg-violet-50/30">
                    <td className="px-4 py-2 text-slate-500">{p.pid}</td>
                    <td className="px-4 py-2 text-slate-900 font-semibold">{p.name}</td>
                    <td className="px-4 py-2 text-slate-600">{p.username}</td>
                    <td className="px-4 py-2 text-right font-semibold text-rose-700">{p.cpu_percent.toFixed(1)}%</td>
                    <td className="px-4 py-2 text-right font-semibold text-violet-700">{p.memory_percent.toFixed(1)}%</td>
                  </tr>
                ))}
                {processes.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-slate-400 font-sans">
                      No process snapshot available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel overflow-hidden">
          <div className="panel-header">
            <h3 className="text-sm font-semibold text-slate-900">Recent Server Logs</h3>
            <Link to={`/logs?server_id=${server.id}`} className="text-xs font-semibold text-amber-700 hover:text-amber-900">
              Open in Log Explorer &rarr;
            </Link>
          </div>
          <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto font-mono text-xs">
            {logs.length === 0 ? (
              <p className="p-6 text-center text-slate-400 font-sans">No logs ingested for this server.</p>
            ) : (
              logs.map((lg) => (
                <div key={lg.id} className="px-4 py-2.5 flex items-start gap-2.5 hover:bg-slate-50">
                  <SeverityBadge severity={lg.severity} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] text-slate-500">
                      {formatDateTime(lg.timestamp)} · <span className="text-slate-800 font-semibold">{lg.source}</span>
                    </p>
                    <p className="text-slate-700 mt-0.5 break-words">{lg.message}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
