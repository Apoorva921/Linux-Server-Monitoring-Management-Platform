import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { StatusBadge } from '../components/StatusBadge';
import { AlertsPage } from '../pages/AlertsPage';
import { OverviewPage } from '../pages/OverviewPage';
import * as api from '../services/api';

vi.mock('../hooks/useMetricsWebSocket', () => ({
  useMetricsWebSocket: () => ({
    connectionState: 'connected',
    lastEventAt: new Date().toISOString(),
    addListener: () => () => {},
    subscribeTopic: vi.fn(),
    unsubscribeTopic: vi.fn(),
  }),
}));

describe('SentinelOps Frontend Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders all server status indicator badges accurately', () => {
    render(
      <div>
        <StatusBadge status="healthy" />
        <StatusBadge status="warning" />
        <StatusBadge status="critical" />
        <StatusBadge status="offline" />
      </div>,
    );

    expect(screen.getByText('Healthy')).toBeInTheDocument();
    expect(screen.getByText('Warning')).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
    expect(screen.getByText('Offline')).toBeInTheDocument();
  });

  it('renders Overview dashboard with real API summary data and DEMO DATA labeling', async () => {
    vi.spyOn(api.dashboardApi, 'getSummary').mockResolvedValue({
      total_servers: 2,
      online_servers: 2,
      offline_servers: 0,
      healthy_servers: 1,
      warning_servers: 1,
      critical_servers: 0,
      active_alerts: 1,
      critical_alerts: 0,
      warning_alerts: 1,
      avg_cpu_percent: 48.5,
      avg_memory_percent: 62.0,
      avg_disk_percent: 51.3,
      total_net_upload_bps: 1048576,
      total_net_download_bps: 2097152,
      has_demo_data: true,
      has_real_data: false,
      servers: [
        {
          id: 'srv-1',
          hostname: 'prod-web-01.demo.internal',
          display_name: 'prod-web-01 [DEMO]',
          ip_address: '10.20.1.11',
          os_name: 'Ubuntu',
          os_version: '24.04 LTS',
          kernel_version: '6.8.0',
          architecture: 'x86_64',
          cpu_cores: 8,
          total_memory_mb: 16384,
          total_disk_gb: 250,
          agent_version: '1.0.0',
          status: 'healthy',
          health_score: 96,
          health_explanation: null,
          uptime_seconds: 86400,
          load_avg_1m: 0.9,
          load_avg_5m: 0.8,
          load_avg_15m: 0.7,
          last_heartbeat: new Date().toISOString(),
          is_demo: true,
          tags: ['demo'],
          created_at: new Date().toISOString(),
          latest_metric: {
            timestamp: new Date().toISOString(),
            cpu_percent: 48.5,
            memory_percent: 62.0,
            memory_used_mb: 10158,
            memory_total_mb: 16384,
            disk_percent: 51.3,
            disk_used_gb: 128,
            disk_total_gb: 250,
            net_upload_bps: 1048576,
            net_download_bps: 2097152,
            net_bytes_sent: 5000000,
            net_bytes_recv: 9000000,
            net_packets_sent: 1000,
            net_packets_recv: 2000,
            net_interface: 'eth0',
            load_1m: 0.9,
            load_5m: 0.8,
            load_15m: 0.7,
            uptime_seconds: 86400,
            process_count: 112,
          },
          active_alert_count: 0,
        },
      ],
      recent_alerts: [],
      recent_logs: [],
      trend_series: [],
      generated_at: new Date().toISOString(),
    });

    render(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Infrastructure Overview')).toBeInTheDocument();
    });
    expect(screen.getByText('2 / 2')).toBeInTheDocument();
    expect(screen.getAllByText('48.5%').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('prod-web-01 [DEMO]')).toBeInTheDocument();
    expect(screen.getAllByText('DEMO DATA').length).toBeGreaterThanOrEqual(1);
  });

  it('displays API error banner cleanly when summary fetch fails', async () => {
    vi.spyOn(api.dashboardApi, 'getSummary').mockRejectedValue(new Error('Backend unreachable'));

    render(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Backend unreachable');
    });
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('supports acknowledging and resolving alerts interactively', async () => {
    const user = userEvent.setup();
    const mockAlert = {
      id: 'alert-1',
      server_id: 'srv-1',
      server_name: 'ubuntu-prod-01',
      rule_id: null,
      metric_type: 'cpu',
      title: 'CRITICAL: High CPU Utilization on ubuntu-prod-01',
      description: 'CPU reached 94.2% (threshold: 90%).',
      severity: 'critical' as const,
      metric_value: 94.2,
      threshold_value: 90,
      status: 'active' as const,
      acknowledged_by: null,
      acknowledged_at: null,
      resolved_at: null,
      is_demo: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    vi.spyOn(api.serversApi, 'list').mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      total_pages: 1,
    });
    vi.spyOn(api.alertsApi, 'list').mockResolvedValue({
      items: [mockAlert],
      total: 1,
      page: 1,
      page_size: 100,
      total_pages: 1,
    });
    vi.spyOn(api.alertsApi, 'summary').mockResolvedValue({
      total: 1,
      active: 1,
      acknowledged: 0,
      resolved: 0,
      critical_active: 1,
      warning_active: 0,
    });
    const ackSpy = vi.spyOn(api.alertsApi, 'acknowledge').mockResolvedValue({
      ...mockAlert,
      status: 'acknowledged',
    });
    const resolveSpy = vi.spyOn(api.alertsApi, 'resolve').mockResolvedValue({
      ...mockAlert,
      status: 'resolved',
    });

    render(
      <MemoryRouter>
        <AlertsPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/CRITICAL: High CPU Utilization/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /acknowledge/i }));
    await waitFor(() => expect(ackSpy).toHaveBeenCalledWith('alert-1'));

    await user.click(screen.getByRole('button', { name: /resolve/i }));
    await waitFor(() => expect(resolveSpy).toHaveBeenCalledWith('alert-1'));
  });
});

