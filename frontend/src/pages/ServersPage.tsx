import React, { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ErrorBanner, LoadingSpinner } from '../components/Feedback';
import { DemoBadge, StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../hooks/AuthContext';
import { serversApi } from '../services/api';
import type { Server, ServerRegisterResponse } from '../types';
import { extractErrorMessage, formatRelativeTime, formatUptime } from '../utils/format';

export const ServersPage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const isAdmin = user?.role === 'admin';

  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState<string>(searchParams.get('search') || '');

  const [showModal, setShowModal] = useState(false);
  const [hostname, setHostname] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [ipAddress, setIpAddress] = useState('');
  const [osName, setOsName] = useState('Ubuntu');
  const [osVersion, setOsVersion] = useState('24.04 LTS');
  const [registering, setRegistering] = useState(false);
  const [createdAgent, setCreatedAgent] = useState<ServerRegisterResponse | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const loadServers = useCallback(async () => {
    try {
      const res = await serversApi.list({
        status: statusFilter || undefined,
        search: search.trim() || undefined,
        page_size: 100,
      });
      setServers(res.items);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to fetch servers.'));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search]);

  useEffect(() => {
    loadServers();
  }, [loadServers]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegistering(true);
    setError(null);
    try {
      const res = await serversApi.register({
        hostname: hostname.trim(),
        display_name: displayName.trim() || hostname.trim(),
        ip_address: ipAddress.trim() || '0.0.0.0',
        os_name: osName.trim(),
        os_version: osVersion.trim(),
      });
      setCreatedAgent(res);
      setHostname('');
      setDisplayName('');
      setIpAddress('');
      await loadServers();
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to register monitoring agent.'));
    } finally {
      setRegistering(false);
    }
  };

  const handleDelete = async (srv: Server) => {
    if (!window.confirm(`Delete server "${srv.display_name}" and all its metrics, alerts, and logs?`)) return;
    try {
      await serversApi.remove(srv.id);
      await loadServers();
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to delete server.'));
    }
  };

  const copyText = (key: string, value: string) => {
    navigator.clipboard?.writeText(value);
    setCopiedField(key);
    window.setTimeout(() => setCopiedField(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Server Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Register Linux monitoring agents, inspect host inventory, and monitor heartbeats
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadServers}
            className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700"
          >
            Refresh
          </button>
          {isAdmin && (
            <button
              type="button"
              onClick={() => {
                setCreatedAgent(null);
                setShowModal(true);
              }}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition-colors"
            >
              + Register Agent
            </button>
          )}
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadServers} />}

      {/* Filters */}
      <div className="panel p-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            if (!e.target.value && searchParams.has('search')) {
              setSearchParams({});
            }
          }}
          placeholder="Filter by hostname, IP address, or OS..."
          className="flex-1 min-w-[220px] bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-emerald-400"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-400"
        >
          <option value="">All Statuses</option>
          <option value="healthy">Healthy</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
          <option value="offline">Offline</option>
        </select>
      </div>

      {/* Server Table */}
      <div className="panel overflow-hidden">
        {loading ? (
          <LoadingSpinner label="Loading server inventory..." />
        ) : servers.length === 0 ? (
          <div className="p-10 text-center space-y-1.5">
            <p className="text-sm text-slate-700 font-semibold">No matching servers found</p>
            <p className="text-xs text-slate-500">
              Register a Linux host using the button above or run the Demo Simulator.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-100 bg-slate-50/80">
                <tr>
                  <th className="px-5 py-3">Hostname / Name</th>
                  <th className="px-4 py-3">IP Address</th>
                  <th className="px-4 py-3">Operating System</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Health</th>
                  <th className="px-4 py-3">Uptime</th>
                  <th className="px-4 py-3">Agent</th>
                  <th className="px-4 py-3">Last Heartbeat</th>
                  {isAdmin && <th className="px-4 py-3 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {servers.map((srv) => (
                  <tr key={srv.id} className="hover:bg-emerald-50/30 transition-colors">
                    <td className="px-5 py-3.5">
                      <Link
                        to={`/servers/${srv.id}`}
                        className="font-semibold text-slate-900 hover:text-indigo-600 flex items-center gap-2"
                      >
                        <span>{srv.display_name}</span>
                        {srv.is_demo && <DemoBadge />}
                      </Link>
                      <span className="text-xs font-mono text-slate-500">{srv.hostname}</span>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-700">{srv.ip_address}</td>
                    <td className="px-4 py-3.5 text-xs text-slate-700">
                      {srv.os_name} <span className="text-slate-400">{srv.os_version}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <StatusBadge status={srv.status} />
                    </td>
                    <td className="px-4 py-3.5 font-mono font-bold text-slate-800">
                      {srv.health_score.toFixed(0)}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-700">
                      {formatUptime(srv.uptime_seconds)}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-500">v{srv.agent_version}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-500">
                      {formatRelativeTime(srv.last_heartbeat)}
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3.5 text-right">
                        <button
                          type="button"
                          onClick={() => handleDelete(srv)}
                          className="px-2.5 py-1 rounded-md text-xs font-medium text-rose-700 hover:bg-rose-50 border border-transparent hover:border-rose-200"
                        >
                          Remove
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Register Agent Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/35 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900">
                {createdAgent ? 'Agent Credentials Issued' : 'Register Linux Monitoring Agent'}
              </h2>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="text-xs font-semibold text-slate-500 hover:text-slate-900"
              >
                Close
              </button>
            </div>

            {!createdAgent ? (
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Hostname *</label>
                    <input
                      type="text"
                      required
                      value={hostname}
                      onChange={(e) => setHostname(e.target.value)}
                      placeholder="ubuntu-api-01"
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:bg-white focus:border-emerald-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Display Name</label>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Production API 01"
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:bg-white focus:border-emerald-400"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">IP Address</label>
                    <input
                      type="text"
                      value={ipAddress}
                      onChange={(e) => setIpAddress(e.target.value)}
                      placeholder="10.0.1.20"
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">OS Name</label>
                    <input
                      type="text"
                      value={osName}
                      onChange={(e) => setOsName(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">OS Version</label>
                    <input
                      type="text"
                      value={osVersion}
                      onChange={(e) => setOsVersion(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={registering}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold disabled:opacity-50"
                  >
                    {registering ? 'Registering...' : 'Generate Server ID & API Token'}
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900 font-medium">
                  {createdAgent.warning}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Server ID</label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-indigo-50/60 border border-indigo-200 rounded-lg px-3 py-2 text-xs font-mono text-indigo-800 truncate">
                      {createdAgent.server.id}
                    </code>
                    <button
                      type="button"
                      onClick={() => copyText('id', createdAgent.server.id)}
                      className="px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700"
                    >
                      Copy
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Agent API Token (One-Time)</label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-xs font-mono text-emerald-800 break-all">
                      {createdAgent.api_token}
                    </code>
                    <button
                      type="button"
                      onClick={() => copyText('token', createdAgent.api_token)}
                      className="px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700"
                    >
                      Copy
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Ubuntu Agent Install Command</label>
                  <pre className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-[11px] font-mono text-slate-700 overflow-x-auto">
{`sudo bash scripts/install_agent_ubuntu.sh \\
  --api-url ${window.location.origin} \\
  --server-id ${createdAgent.server.id} \\
  --api-token ${createdAgent.api_token}`}
                  </pre>
                </div>

                {copiedField && (
                  <p className="text-xs font-semibold text-emerald-700">Copied {copiedField} to clipboard.</p>
                )}

                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
