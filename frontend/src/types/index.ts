export type UserRole = 'admin' | 'viewer';

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface HealthDeduction {
  factor: string;
  value: string;
  impact: number;
  reason: string;
}

export interface HealthExplanation {
  score: number;
  status: ServerStatus;
  summary: string;
  deductions: HealthDeduction[];
}

export type ServerStatus = 'healthy' | 'warning' | 'critical' | 'offline';

export interface DiskPartition {
  device: string;
  mountpoint: string;
  fstype: string;
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent: number;
}

export interface ProcessInfo {
  pid: number;
  name: string;
  cpu_percent: number;
  memory_percent: number;
  username: string;
  status: string;
}

export interface ServerMetricBrief {
  timestamp: string;
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  net_upload_bps: number;
  net_download_bps: number;
  net_bytes_sent: number;
  net_bytes_recv: number;
  net_packets_sent: number;
  net_packets_recv: number;
  net_interface: string;
  load_1m: number;
  load_5m: number;
  load_15m: number;
  uptime_seconds: number;
  process_count: number;
}

export interface ServerMetric extends ServerMetricBrief {
  id: number;
  server_id: string;
  cpu_user: number;
  cpu_system: number;
  cpu_iowait: number;
  memory_available_mb: number;
  swap_percent: number;
  disk_partitions: DiskPartition[];
  top_processes: ProcessInfo[];
  is_demo: boolean;
}

export interface Server {
  id: string;
  hostname: string;
  display_name: string;
  ip_address: string;
  os_name: string;
  os_version: string;
  kernel_version: string;
  architecture: string;
  cpu_cores: number;
  total_memory_mb: number;
  total_disk_gb: number;
  agent_version: string;
  status: ServerStatus;
  health_score: number;
  health_explanation: HealthExplanation | null;
  uptime_seconds: number;
  load_avg_1m: number;
  load_avg_5m: number;
  load_avg_15m: number;
  last_heartbeat: string | null;
  is_demo: boolean;
  tags: string[];
  created_at: string;
  latest_metric: ServerMetricBrief | null;
  active_alert_count: number;
}

export interface ServerRegisterResponse {
  server: Server;
  api_token: string;
  token_prefix: string;
  warning: string;
}

export interface Alert {
  id: string;
  server_id: string;
  server_name: string;
  rule_id: string | null;
  metric_type: string;
  title: string;
  description: string;
  severity: 'warning' | 'critical' | 'info';
  metric_value: number;
  threshold_value: number;
  status: 'active' | 'acknowledged' | 'resolved';
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlertSummary {
  total: number;
  active: number;
  acknowledged: number;
  resolved: number;
  critical_active: number;
  warning_active: number;
}

export interface SystemLog {
  id: number;
  server_id: string;
  server_name: string;
  timestamp: string;
  severity: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  source: string;
  hostname: string;
  message: string;
  raw_line: string;
  is_demo: boolean;
  created_at: string;
}

export interface ProcessListResponse {
  server_id: string;
  server_name: string;
  is_demo: boolean;
  timestamp: string | null;
  total_processes: number;
  processes: ProcessInfo[];
}

export interface AlertThresholdConfig {
  metric_type: string;
  name: string;
  warning_threshold: number;
  critical_threshold: number;
  cooldown_seconds: number;
  is_enabled: boolean;
}

export interface SystemSettings {
  monitoring_interval_seconds: number;
  offline_threshold_seconds: number;
  metric_retention_days: number;
  log_sources: string[];
  enable_journalctl: boolean;
  max_processes_per_snapshot: number;
  thresholds: AlertThresholdConfig[];
  updated_at: string;
}

export interface FleetTrendPoint {
  timestamp: string;
  avg_cpu_percent: number;
  avg_memory_percent: number;
  avg_disk_percent: number;
  total_upload_bps: number;
  total_download_bps: number;
}

export interface DashboardSummary {
  total_servers: number;
  online_servers: number;
  offline_servers: number;
  healthy_servers: number;
  warning_servers: number;
  critical_servers: number;
  active_alerts: number;
  critical_alerts: number;
  warning_alerts: number;
  avg_cpu_percent: number;
  avg_memory_percent: number;
  avg_disk_percent: number;
  total_net_upload_bps: number;
  total_net_download_bps: number;
  has_demo_data: boolean;
  has_real_data: boolean;
  servers: Server[];
  recent_alerts: Alert[];
  recent_logs: SystemLog[];
  trend_series: FleetTrendPoint[];
  generated_at: string;
}

export interface WsEvent {
  type: 'connected' | 'metric_update' | 'alert_event' | 'server_status' | 'log_event' | 'pong' | 'subscribed' | 'unsubscribed';
  server_id?: string;
  server_name?: string;
  action?: string;
  is_demo?: boolean;
  timestamp?: string;
  data?: Record<string, unknown>;
}

