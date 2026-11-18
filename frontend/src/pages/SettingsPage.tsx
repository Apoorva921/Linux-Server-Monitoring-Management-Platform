import React, { useEffect, useState } from 'react';
import { ErrorBanner, LoadingSpinner } from '../components/Feedback';
import { useAuth } from '../hooks/AuthContext';
import { settingsApi } from '../services/api';
import type { AlertThresholdConfig, SystemSettings } from '../types';
import { extractErrorMessage } from '../utils/format';

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [logSourcesText, setLogSourcesText] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    settingsApi
      .get()
      .then((res) => {
        setSettings(res);
        setLogSourcesText(res.log_sources.join('\n'));
      })
      .catch((err) => setError(extractErrorMessage(err, 'Failed to load settings.')))
      .finally(() => setLoading(false));
  }, []);

  const updateThreshold = (idx: number, patch: Partial<AlertThresholdConfig>) => {
    setSettings((prev) => {
      if (!prev) return prev;
      const copy = [...prev.thresholds];
      copy[idx] = { ...copy[idx], ...patch };
      return { ...prev, thresholds: copy };
    });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings || !isAdmin) return;
    setSaving(true);
    setError(null);
    setSavedMsg(null);
    try {
      const updated = await settingsApi.update({
        monitoring_interval_seconds: settings.monitoring_interval_seconds,
        offline_threshold_seconds: settings.offline_threshold_seconds,
        metric_retention_days: settings.metric_retention_days,
        log_sources: logSourcesText
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
        enable_journalctl: settings.enable_journalctl,
        max_processes_per_snapshot: settings.max_processes_per_snapshot,
        thresholds: settings.thresholds,
      });
      setSettings(updated);
      setSavedMsg('Settings saved and applied to the alert evaluation engine.');
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to save settings.'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner label="Loading platform configuration..." />;
  if (!settings) return <ErrorBanner message={error || 'Unable to load settings.'} />;

  return (
    <form onSubmit={handleSave} className="space-y-6 max-w-4xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Platform Settings</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure monitoring intervals, alert thresholds, metric retention, and Linux log collection
          </p>
        </div>
        {isAdmin ? (
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        ) : (
          <span className="text-xs font-mono text-amber-800 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-lg">
            Read-only (Administrator role required to edit)
          </span>
        )}
      </div>

      {error && <ErrorBanner message={error} />}
      {savedMsg && (
        <div className="px-4 py-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium">
          {savedMsg}
        </div>
      )}

      {/* Collection & Retention */}
      <div className="panel p-5 space-y-4">
        <h2 className="text-sm font-bold text-slate-900">Collection &amp; Retention Policy</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Monitoring Interval (seconds)</label>
            <input
              type="number"
              min={2}
              max={300}
              disabled={!isAdmin}
              value={settings.monitoring_interval_seconds}
              onChange={(e) =>
                setSettings({ ...settings, monitoring_interval_seconds: Number(e.target.value) })
              }
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono text-slate-900 disabled:opacity-60"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Offline Heartbeat Timeout (sec)</label>
            <input
              type="number"
              min={10}
              max={3600}
              disabled={!isAdmin}
              value={settings.offline_threshold_seconds}
              onChange={(e) =>
                setSettings({ ...settings, offline_threshold_seconds: Number(e.target.value) })
              }
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono text-slate-900 disabled:opacity-60"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Metric &amp; Log Retention (days)</label>
            <input
              type="number"
              min={1}
              max={365}
              disabled={!isAdmin}
              value={settings.metric_retention_days}
              onChange={(e) => setSettings({ ...settings, metric_retention_days: Number(e.target.value) })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono text-slate-900 disabled:opacity-60"
            />
          </div>
        </div>
      </div>

      {/* Alert Thresholds */}
      <div className="panel p-5 space-y-4">
        <div>
          <h2 className="text-sm font-bold text-slate-900">Global Alert Thresholds</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            CPU/Memory/Disk thresholds are percentages (%). Network thresholds are throughput in MB/s.
          </p>
        </div>

        <div className="space-y-3">
          {settings.thresholds.map((rule, idx) => (
            <div
              key={rule.metric_type}
              className="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/80 grid grid-cols-1 sm:grid-cols-12 gap-3 items-center"
            >
              <div className="sm:col-span-4">
                <p className="text-xs font-bold text-slate-900">{rule.name}</p>
                <p className="text-[11px] font-mono text-slate-500">{rule.metric_type}</p>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-[10px] font-bold text-amber-700 uppercase mb-1">Warning</label>
                <input
                  type="number"
                  step="0.5"
                  disabled={!isAdmin}
                  value={rule.warning_threshold}
                  onChange={(e) => updateThreshold(idx, { warning_threshold: Number(e.target.value) })}
                  className="w-full bg-white border border-amber-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-[10px] font-bold text-rose-700 uppercase mb-1">Critical</label>
                <input
                  type="number"
                  step="0.5"
                  disabled={!isAdmin}
                  value={rule.critical_threshold}
                  onChange={(e) => updateThreshold(idx, { critical_threshold: Number(e.target.value) })}
                  className="w-full bg-white border border-rose-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Cooldown (s)</label>
                <input
                  type="number"
                  min={10}
                  disabled={!isAdmin}
                  value={rule.cooldown_seconds}
                  onChange={(e) => updateThreshold(idx, { cooldown_seconds: Number(e.target.value) })}
                  className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900"
                />
              </div>
              <div className="sm:col-span-2 flex items-center justify-end gap-2">
                <label className="text-xs font-medium text-slate-600">Enabled</label>
                <input
                  type="checkbox"
                  disabled={!isAdmin}
                  checked={rule.is_enabled}
                  onChange={(e) => updateThreshold(idx, { is_enabled: e.target.checked })}
                  className="rounded border-slate-300 text-teal-600"
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Log Collection Config */}
      <div className="panel p-5 space-y-4">
        <h2 className="text-sm font-bold text-slate-900">Linux Log Collection Configuration</h2>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">
            Approved Log Paths (one per line, read with least-privilege permissions)
          </label>
          <textarea
            rows={3}
            disabled={!isAdmin}
            value={logSourcesText}
            onChange={(e) => setLogSourcesText(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono text-slate-900 disabled:opacity-60"
          />
        </div>
        <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-700">
          <input
            type="checkbox"
            disabled={!isAdmin}
            checked={settings.enable_journalctl}
            onChange={(e) => setSettings({ ...settings, enable_journalctl: e.target.checked })}
          />
          Collect systemd journal events via read-only <code>journalctl</code> when available
        </label>
      </div>
    </form>
  );
};
