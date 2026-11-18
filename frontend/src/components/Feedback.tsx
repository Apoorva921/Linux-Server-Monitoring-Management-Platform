import React from 'react';

export const ErrorBanner: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div
    role="alert"
    className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm"
  >
    <span className="font-medium break-words">{message}</span>
    {onRetry && (
      <button
        type="button"
        onClick={onRetry}
        className="px-3 py-1 rounded-lg bg-white hover:bg-rose-100 border border-rose-200 text-xs font-semibold text-rose-700 transition-colors shrink-0"
      >
        Retry
      </button>
    )}
  </div>
);

export const LoadingSpinner: React.FC<{ label?: string }> = ({ label = 'Loading telemetry...' }) => (
  <div className="flex flex-col items-center justify-center py-16 text-slate-500 gap-3">
    <div className="w-6 h-6 border-2 border-slate-200 border-t-indigo-600 rounded-full animate-spin" />
    <span className="text-xs font-medium">{label}</span>
  </div>
);
