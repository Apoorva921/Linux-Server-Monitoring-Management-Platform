import React from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatBps, formatTimeShort } from '../utils/format';

interface ChartPoint {
  timestamp: string;
  [key: string]: string | number;
}

interface ResourceChartProps {
  title: string;
  subtitle?: string;
  data: ChartPoint[];
  dataKey: string;
  color: string;
  unit?: string;
  maxDomain?: number;
  height?: number;
}

export const ResourceAreaChart: React.FC<ResourceChartProps> = ({
  title,
  subtitle,
  data,
  dataKey,
  color,
  unit = '%',
  maxDomain = 100,
  height = 220,
}) => {
  const gradientId = `grad-${dataKey}-${color.replace('#', '')}`;

  return (
    <div className="panel flex flex-col">
      <div className="panel-header">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
        {data.length > 0 && (
          <span
            className="text-sm font-mono font-bold px-2.5 py-0.5 rounded-full"
            style={{ backgroundColor: `${color}18`, color }}
          >
            {Number(data[data.length - 1][dataKey] ?? 0).toFixed(1)}
            {unit}
          </span>
        )}
      </div>
      <div className="p-4" style={{ height }}>
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-400">
            Waiting for telemetry samples...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.22} />
                  <stop offset="95%" stopColor={color} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTimeShort}
                stroke="#cbd5e1"
                tick={{ fontSize: 11, fill: '#64748b' }}
                minTickGap={28}
              />
              <YAxis
                domain={[0, maxDomain]}
                stroke="#cbd5e1"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(v) => `${v}${unit}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e2e8f0',
                  borderRadius: '10px',
                  fontSize: '12px',
                  color: '#0f172a',
                  boxShadow: '0 8px 24px rgba(15,23,42,0.08)',
                }}
                labelFormatter={(l) => formatTimeShort(String(l))}
                formatter={(val: unknown) => [`${Number(val).toFixed(2)}${unit}`, title]}
              />
              <Area
                type="monotone"
                dataKey={dataKey}
                stroke={color}
                strokeWidth={2.2}
                fillOpacity={1}
                fill={`url(#${gradientId})`}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

interface NetworkThroughputChartProps {
  title?: string;
  subtitle?: string;
  data: ChartPoint[];
  uploadKey: string;
  downloadKey: string;
  height?: number;
}

export const NetworkThroughputChart: React.FC<NetworkThroughputChartProps> = ({
  title = 'Network Throughput',
  subtitle = 'Live upload & download rate (bytes/sec)',
  data,
  uploadKey,
  downloadKey,
  height = 220,
}) => {
  return (
    <div className="panel flex flex-col">
      <div className="panel-header">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
        </div>
        {data.length > 0 && (
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 font-semibold">
              In {formatBps(Number(data[data.length - 1][downloadKey] ?? 0))}
            </span>
            <span className="px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 font-semibold">
              Out {formatBps(Number(data[data.length - 1][uploadKey] ?? 0))}
            </span>
          </div>
        )}
      </div>
      <div className="p-4" style={{ height }}>
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-400">
            Waiting for network telemetry...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTimeShort}
                stroke="#cbd5e1"
                tick={{ fontSize: 11, fill: '#64748b' }}
                minTickGap={28}
              />
              <YAxis
                stroke="#cbd5e1"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(v) => formatBps(Number(v))}
                width={74}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e2e8f0',
                  borderRadius: '10px',
                  fontSize: '12px',
                  color: '#0f172a',
                  boxShadow: '0 8px 24px rgba(15,23,42,0.08)',
                }}
                labelFormatter={(l) => formatTimeShort(String(l))}
                formatter={(val: unknown, name: string) => [formatBps(Number(val)), name]}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Line
                type="monotone"
                dataKey={downloadKey}
                name="Download"
                stroke="#0284c7"
                strokeWidth={2.2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey={uploadKey}
                name="Upload"
                stroke="#0d9488"
                strokeWidth={2.2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
