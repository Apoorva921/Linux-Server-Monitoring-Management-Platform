import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ErrorBanner, LoadingSpinner } from '../components/Feedback';
import { DemoBadge, SeverityBadge } from '../components/StatusBadge';
import { logsApi, serversApi } from '../services/api';
import type { Server, SystemLog } from '../types';
import { extractErrorMessage, formatDateTime } from '../utils/format';

export const LogsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [total, setTotal] = useState(0);
  const [servers, setServers] = useState<Server[]>([]);
  const [keyword, setKeyword] = useState('');
  const [severity, setSeverity] = useState('');
  const [serverId, setServerId] = useState(searchParams.get('server_id') || '');
  const [startDate, setStartDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    serversApi
      .list({ page_size: 100 })
      .then((res) => setServers(res.items))
      .catch(() => {});
  }, []);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await logsApi.search({
        q: keyword.trim() || undefined,
        severity: severity || undefined,
        server_id: serverId || undefined,
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        page_size: 100,
      });
      setLogs(res.items);
      setTotal(res.total);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to query system logs.'));
    } finally {
      setLoading(false);
    }
  }, [keyword, severity, serverId, startDate]);

  useEffect(() => {
    const t = window.setTimeout(loadLogs, 200);
    return () => window.clearTimeout(t);
  }, [loadLogs]);

  const rowHighlight = (sev: string) => {
    if (sev === 'CRITICAL') return 'bg-rose-50/90 border-l-4 border-l-rose-500';
    if (sev === 'ERROR') return 'bg-red-50/70 border-l-4 border-l-red-400';
    if (sev === 'WARNING') return 'bg-amber-50/70 border-l-4 border-l-amber-400';
    return 'border-l-4 border-l-transparent';
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">System Log Explorer</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Search and filter Linux syslog, auth.log, and journalctl events across monitored hosts
          </p>
        </div>
        <button
          type="button"
          onClick={loadLogs}
          className="px-3.5 py-2 rounded-lg bg-white hover:bg-amber-50 border border-slate-200 text-xs font-semibold text-slate-700"
        >
          Refresh ({total})
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadLogs} />}

      {/* Filter Toolbar */}
      <div className="panel p-4 grid grid-cols-1 md:grid-cols-4 gap-3">
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="Search log messages, sources, hostnames..."
          className="md:col-span-2 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-amber-400"
        />

        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800"
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="ERROR">ERROR</option>
          <option value="WARNING">WARNING</option>
          <option value="INFO">INFO</option>
          <option value="DEBUG">DEBUG</option>
        </select>

        <div className="flex gap-2">
          <select
            value={serverId}
            onChange={(e) => setServerId(e.target.value)}
            className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 min-w-0"
          >
            <option value="">All Servers</option>
            {servers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.display_name}
              </option>
            ))}
          </select>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            title="Filter logs from date"
            className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-2 text-xs text-slate-800"
          />
        </div>
      </div>

      {/* Scrollable Log Table */}
      <div className="panel overflow-hidden">
        {loading ? (
          <LoadingSpinner label="Querying logs..." />
        ) : logs.length === 0 ? (
          <div className="p-10 text-center text-sm text-slate-500">
            No log entries found for the selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="sticky top-0 bg-slate-50 text-slate-500 border-b border-slate-200 z-10">
                <tr>
                  <th className="px-4 py-3 whitespace-nowrap">Timestamp</th>
                  <th className="px-3 py-3">Severity</th>
                  <th className="px-3 py-3">Server</th>
                  <th className="px-3 py-3">Source</th>
                  <th className="px-4 py-3 w-full">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((lg) => (
                  <tr key={lg.id} className={`hover:bg-slate-50 ${rowHighlight(lg.severity)}`}>
                    <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">
                      {formatDateTime(lg.timestamp)}
                    </td>
                    <td className="px-3 py-2.5 whitespace-nowrap">
                      <SeverityBadge severity={lg.severity} />
                    </td>
                    <td className="px-3 py-2.5 text-indigo-700 font-semibold whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5">
                        {lg.server_name}
                        {lg.is_demo && <DemoBadge />}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-slate-700 whitespace-nowrap">{lg.source}</td>
                    <td className="px-4 py-2.5 text-slate-800 break-words">{lg.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
