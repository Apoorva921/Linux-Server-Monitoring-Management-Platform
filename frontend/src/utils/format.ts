export function formatBytes(bytes: number, decimals = 1): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.min(sizes.length - 1, Math.floor(Math.log(bytes) / Math.log(k)));
  return `${(bytes / Math.pow(k, i)).toFixed(decimals)} ${sizes[i]}`;
}

export function formatBps(bps: number): string {
  if (!Number.isFinite(bps) || bps <= 0) return '0 B/s';
  return `${formatBytes(bps, 1)}/s`;
}

export function formatUptime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0m';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h ${mins}m`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return 'Never';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return 'Unknown';
  const diffSec = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
  if (diffSec < 5) return 'Just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

export function formatTimeShort(iso: string): string {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  return dt.toLocaleString([], {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function extractErrorMessage(err: unknown, fallback = 'An unexpected error occurred.'): string {
  if (typeof err === 'object' && err !== null) {
    const anyErr = err as {
      response?: {
        data?: {
          message?: string;
          details?: Array<{ loc?: Array<string | number>; msg?: string }>;
          detail?: string | { message?: string };
        };
      };
      message?: string;
    };
    const data = anyErr.response?.data;
    if (Array.isArray(data?.details) && data.details.length > 0) {
      const formatted = data.details.map((d) => {
        const field = d.loc && d.loc.length > 0 ? String(d.loc[d.loc.length - 1]) : 'field';
        const label = field.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
        return `${label}: ${d.msg || 'invalid value'}`;
      });
      return formatted.join(' · ');
    }
    if (data?.message) return data.message;
    if (typeof data?.detail === 'string') return data.detail;
    if (typeof data?.detail === 'object' && data?.detail?.message) return data.detail.message;
    if (anyErr.message) return anyErr.message;
  }
  return fallback;
}
