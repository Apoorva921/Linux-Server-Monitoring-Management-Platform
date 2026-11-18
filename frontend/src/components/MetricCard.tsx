import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  accent?: 'sky' | 'emerald' | 'amber' | 'rose' | 'indigo' | 'teal' | 'slate';
  percent?: number;
}

const ACCENT_MAP = {
  sky: {
    card: 'bg-sky-50/70 border-sky-200/80 border-t-sky-500',
    label: 'text-sky-800',
    bar: 'bg-sky-500',
    track: 'bg-sky-200/60',
  },
  emerald: {
    card: 'bg-emerald-50/70 border-emerald-200/80 border-t-emerald-500',
    label: 'text-emerald-800',
    bar: 'bg-emerald-500',
    track: 'bg-emerald-200/60',
  },
  amber: {
    card: 'bg-amber-50/75 border-amber-200/80 border-t-amber-500',
    label: 'text-amber-800',
    bar: 'bg-amber-500',
    track: 'bg-amber-200/60',
  },
  rose: {
    card: 'bg-rose-50/75 border-rose-200/80 border-t-rose-500',
    label: 'text-rose-800',
    bar: 'bg-rose-500',
    track: 'bg-rose-200/60',
  },
  indigo: {
    card: 'bg-violet-50/75 border-violet-200/80 border-t-violet-500',
    label: 'text-violet-800',
    bar: 'bg-violet-500',
    track: 'bg-violet-200/60',
  },
  teal: {
    card: 'bg-teal-50/75 border-teal-200/80 border-t-teal-500',
    label: 'text-teal-800',
    bar: 'bg-teal-500',
    track: 'bg-teal-200/60',
  },
  slate: {
    card: 'bg-slate-50 border-slate-200 border-t-slate-500',
    label: 'text-slate-700',
    bar: 'bg-slate-500',
    track: 'bg-slate-200',
  },
};

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtitle,
  accent = 'sky',
  percent,
}) => {
  const palette = ACCENT_MAP[accent];
  const dynamicBar =
    percent !== undefined
      ? percent >= 90
        ? 'bg-rose-500'
        : percent >= 75
          ? 'bg-amber-500'
          : palette.bar
      : palette.bar;

  return (
    <div className={`rounded-xl border border-t-4 p-4 transition-colors ${palette.card}`}>
      <p className={`text-[11px] font-semibold uppercase tracking-wider ${palette.label}`}>{label}</p>
      <p className="mt-1.5 text-2xl font-bold font-mono text-slate-900 truncate">{value}</p>
      {subtitle && <p className="mt-1 text-xs text-slate-600 truncate">{subtitle}</p>}
      {percent !== undefined && (
        <div className={`mt-3 h-1.5 w-full rounded-full overflow-hidden ${palette.track}`}>
          <div
            className={`h-full rounded-full transition-all duration-500 ${dynamicBar}`}
            style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
          />
        </div>
      )}
    </div>
  );
};
