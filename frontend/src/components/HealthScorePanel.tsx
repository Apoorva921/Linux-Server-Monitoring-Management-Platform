import React from 'react';
import type { HealthExplanation, ServerStatus } from '../types';

interface HealthScorePanelProps {
  score: number;
  status: ServerStatus;
  explanation: HealthExplanation | null;
}

export const HealthScorePanel: React.FC<HealthScorePanelProps> = ({ score, status, explanation }) => {
  const pillStyle =
    status === 'healthy'
      ? 'text-emerald-800 border-emerald-200 bg-emerald-50'
      : status === 'warning'
        ? 'text-amber-800 border-amber-200 bg-amber-50'
        : status === 'critical'
          ? 'text-rose-800 border-rose-200 bg-rose-50'
          : 'text-slate-600 border-slate-200 bg-slate-100';

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Deterministic Health Score</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Rule-based score (0–100) derived from CPU, Memory, Disk, Availability & Alerts
          </p>
        </div>
        <span className="text-xs font-mono font-semibold uppercase text-slate-500">{status}</span>
      </div>

      <div className="p-5 flex flex-col md:flex-row gap-5 items-start md:items-center">
        <div
          className={`px-6 py-4 rounded-xl border-2 flex flex-col items-center justify-center shrink-0 min-w-[110px] ${pillStyle}`}
        >
          <span className="text-3xl font-bold font-mono leading-none">{score.toFixed(0)}</span>
          <span className="text-[11px] uppercase tracking-wider opacity-75 mt-1">out of 100</span>
        </div>

        <div className="flex-1 min-w-0 space-y-3 w-full">
          <p className="text-sm text-slate-700 font-medium">
            {explanation?.summary || 'No health assessment computed yet.'}
          </p>

          {explanation && explanation.deductions.length > 0 ? (
            <div className="space-y-1.5">
              {explanation.deductions.map((d, idx) => (
                <div
                  key={`${d.factor}-${idx}`}
                  className="flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-lg bg-rose-50/60 border border-rose-200/70 text-xs"
                >
                  <div className="min-w-0">
                    <span className="font-semibold text-slate-900">{d.factor}</span>
                    <span className="text-slate-600 ml-2 font-mono">({d.value})</span>
                    <p className="text-slate-600 mt-0.5">{d.reason}</p>
                  </div>
                  <span className="font-mono font-bold text-rose-700 shrink-0">
                    {d.impact.toFixed(1)} pts
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-emerald-700 font-medium">
              0 deductions applied — all monitored indicators are within optimal thresholds.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
