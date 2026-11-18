import React, { useCallback, useEffect, useState } from 'react';
import { ErrorBanner, LoadingSpinner } from '../components/Feedback';
import { DemoBadge, StatusBadge } from '../components/StatusBadge';
import { NetworkThroughputChart, ResourceAreaChart } from '../components/TelemetryCharts';
import { useMetricsWebSocket } from '../hooks/useMetricsWebSocket';
import { serversApi } from '../services/api';
import type { Server, ServerMetric } from '../types';
import { extractErrorMessage, formatBytes } from '../utils/format';

type RangeKey = '15m' | '1h' | '6h' | '24h' | '7d';

export const MonitoringPage: React.FC = () => {
  const { addListener } = useMetricsWebSocket();
  const [servers, setServers] = useState<Server[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [range, setRange] = useState<RangeKey>('1h');
  const [history, setHistory] = useState<ServerMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    serversApi
      .list({ page_size: 100 })
      .then((res) => {
        setServers(res.items);
        if (res.items.length > 0) {
          setSelectedId((prev) => prev || res.items[0].id);
        }
      })
      .catch((err) => setError(extractErrorMessage(err, 'Failed to load server list.')))
      .finally(() => setLoading(false));
  }, []);

  const loadHistory = useCallback(async () => {
    if (!selectedId) return;
    try {
      const data = await serversApi.getMetricsHistory(selectedId, range, 200);
      setHistory(data);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load metric history.'));
    }
  }, [selectedId, range]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    return addListener((evt) => {
      if (evt.type === 'metric_update' && evt.server_id === selectedId && evt.data) {
        const d = evt.data;
        setHistory((prev) => [
          ...prev.slice(-199),
          {
            id: Date.now(),
            server_id: selectedId,
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
          },
        ]);
      }
    });
  }, [addListener, selectedId]);

  if (loading) return <LoadingSpinner label="Initializing real-time monitoring..." />;

  const selectedServer = servers.find((s) => s.id === selectedId);
  const latest = history[history.length - 1];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Real-Time Monitoring</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Live WebSocket telemetry streaming for CPU, RAM, Disk, and Network I/O
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-sky-400"
          >
            {servers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.display_name} ({s.ip_address})
              </option>
            ))}
          </select>

          <div className="flex items-center gap-1 p-1 rounded-lg bg-white border border-slate-200">
            {(['15m', '1h', '6h', '24h', '7d'] as RangeKey[]).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRange(r)}
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold ${
                  range === r ? 'bg-sky-600 text-white' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadHistory} />}

      {!selectedServer ? (
        <div className="panel p-10 text-center text-slate-500 text-sm">
          No servers registered yet.
        </div>
      ) : (
        <>
          <div className="rounded-xl bg-sky-50/70 border border-sky-200/80 px-5 py-3.5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="font-bold text-slate-900">{selectedServer.display_name}</span>
              <StatusBadge status={selectedServer.status} />
              {selectedServer.is_demo && <DemoBadge />}
            </div>
            <div className="flex items-center gap-5 text-xs font-mono text-slate-700">
              <span>
                Load: {selectedServer.load_avg_1m.toFixed(2)} / {selectedServer.load_avg_5m.toFixed(2)} /{' '}
                {selectedServer.load_avg_15m.toFixed(2)}
              </span>
              {latest && (
                <span>
                  Cumulative TX/RX: {formatBytes(latest.net_bytes_sent)} / {formatBytes(latest.net_bytes_recv)}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ResourceAreaChart
              title="CPU Utilization (%)"
              subtitle="Live CPU usage percentage"
              data={history as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
              dataKey="cpu_percent"
              color="#f43f5e"
              height={250}
            />
            <ResourceAreaChart
              title="Memory Utilization (%)"
              subtitle="Live RAM usage percentage"
              data={history as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
              dataKey="memory_percent"
              color="#7c3aed"
              height={250}
            />
            <ResourceAreaChart
              title="Disk Utilization (%)"
              subtitle="Monitored filesystem capacity"
              data={history as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
              dataKey="disk_percent"
              color="#d97706"
              height={250}
            />
            <NetworkThroughputChart
              title="Network Throughput (Live B/s)"
              subtitle="Real-time upload and download throughput"
              data={history as unknown as Array<{ timestamp: string; [key: string]: string | number }>}
              uploadKey="net_upload_bps"
              downloadKey="net_download_bps"
              height={250}
            />
          </div>
        </>
      )}
    </div>
  );
};
