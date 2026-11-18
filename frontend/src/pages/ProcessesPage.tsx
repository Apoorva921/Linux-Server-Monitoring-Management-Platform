import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ErrorBanner, LoadingSpinner } from '../components/Feedback';
import { DemoBadge } from '../components/StatusBadge';
import { serversApi } from '../services/api';
import type { ProcessListResponse, Server } from '../types';
import { extractErrorMessage, formatRelativeTime } from '../utils/format';

type SortField = 'cpu_percent' | 'memory_percent' | 'pid' | 'name';

export const ProcessesPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [servers, setServers] = useState<Server[]>([]);
  const [serverId, setServerId] = useState(searchParams.get('server_id') || '');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortField>('cpu_percent');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [data, setData] = useState<ProcessListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    serversApi
      .list({ page_size: 100 })
      .then((res) => {
        setServers(res.items);
        if (!serverId && res.items.length > 0) {
          setServerId(res.items[0].id);
        }
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [serverId]);

  const loadProcesses = useCallback(async () => {
    if (!serverId) return;
    try {
      const res = await serversApi.getProcesses(serverId, {
        search: search.trim() || undefined,
        sort_by: sortBy,
        order,
      });
      setData(res);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load processes.'));
    }
  }, [serverId, search, sortBy, order]);

  useEffect(() => {
    loadProcesses();
  }, [loadProcesses]);

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setOrder((o) => (o === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(field);
      setOrder(field === 'name' || field === 'pid' ? 'asc' : 'desc');
    }
  };

  const sortArrow = (field: SortField) => (sortBy === field ? (order === 'desc' ? ' ↓' : ' ↑') : '');

  if (loading) return <LoadingSpinner label="Loading process explorer..." />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Process Monitor</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Inspect active processes, CPU/RAM consumers, users, and execution state
          </p>
        </div>
        <span className="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800">
          Read-Only Mode (Termination disabled)
        </span>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadProcesses} />}

      <div className="panel p-4 flex flex-wrap items-center gap-3">
        <select
          value={serverId}
          onChange={(e) => setServerId(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800"
        >
          {servers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.display_name} ({s.ip_address})
            </option>
          ))}
        </select>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter by process name, PID, or username..."
          className="flex-1 min-w-[220px] bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-violet-400"
        />

        <button
          type="button"
          onClick={loadProcesses}
          className="px-3.5 py-2 rounded-lg bg-white hover:bg-violet-50 border border-slate-200 text-xs font-semibold text-slate-700"
        >
          Refresh
        </button>
      </div>

      <div className="panel overflow-hidden">
        {data && (
          <div className="panel-header text-xs text-slate-500 bg-violet-50/40">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900">{data.server_name}</span>
              {data.is_demo && <DemoBadge />}
              <span>· Total OS processes: {data.total_processes}</span>
            </div>
            <span className="font-mono">Snapshot: {formatRelativeTime(data.timestamp)}</span>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="text-slate-500 border-b border-slate-100 bg-slate-50/80">
              <tr>
                <th className="px-5 py-3">
                  <button type="button" onClick={() => toggleSort('pid')} className="hover:text-slate-900 font-semibold">
                    PID{sortArrow('pid')}
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button type="button" onClick={() => toggleSort('name')} className="hover:text-slate-900 font-semibold">
                    Process Name{sortArrow('name')}
                  </button>
                </th>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">
                  <button type="button" onClick={() => toggleSort('cpu_percent')} className="hover:text-slate-900 font-semibold">
                    CPU %{sortArrow('cpu_percent')}
                  </button>
                </th>
                <th className="px-5 py-3 text-right">
                  <button type="button" onClick={() => toggleSort('memory_percent')} className="hover:text-slate-900 font-semibold">
                    Memory %{sortArrow('memory_percent')}
                  </button>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(data?.processes || []).map((p) => (
                <tr key={p.pid} className="hover:bg-violet-50/30">
                  <td className="px-5 py-2.5 text-slate-500">{p.pid}</td>
                  <td className="px-4 py-2.5 font-semibold text-slate-900">{p.name}</td>
                  <td className="px-4 py-2.5 text-slate-600">{p.username}</td>
                  <td className="px-4 py-2.5">
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right text-rose-700 font-bold">
                    {p.cpu_percent.toFixed(1)}%
                  </td>
                  <td className="px-5 py-2.5 text-right text-violet-700 font-bold">
                    {p.memory_percent.toFixed(1)}%
                  </td>
                </tr>
              ))}
              {(!data || data.processes.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-400 font-sans">
                    No process metrics available for this server.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
