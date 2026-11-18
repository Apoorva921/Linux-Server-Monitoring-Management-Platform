import axios from 'axios';
import type {
  Alert,
  AlertSummary,
  DashboardSummary,
  PaginatedResponse,
  ProcessListResponse,
  Server,
  ServerMetric,
  ServerRegisterResponse,
  SystemLog,
  SystemSettings,
  TokenResponse,
  User,
} from '../types';

const TOKEN_STORAGE_KEY = 'sentinelops_jwt';

export const getStoredToken = (): string | null => localStorage.getItem(TOKEN_STORAGE_KEY);
export const setStoredToken = (token: string): void => localStorage.setItem(TOKEN_STORAGE_KEY, token);
export const clearStoredToken = (): void => localStorage.removeItem(TOKEN_STORAGE_KEY);

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response?.status === 401 && !String(error.config?.url || '').includes('/auth/login')) {
      clearStoredToken();
      window.dispatchEvent(new Event('sentinelops:unauthorized'));
    }
    return Promise.reject(error);
  },
);

export const authApi = {
  login: async (username: string, password: string): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>('/auth/login', { username, password });
    return data;
  },
  register: async (payload: {
    username: string;
    email: string;
    password: string;
    full_name: string;
  }): Promise<User> => {
    const { data } = await apiClient.post<User>('/auth/register', payload);
    return data;
  },
  me: async (): Promise<User> => {
    const { data } = await apiClient.get<User>('/auth/me');
    return data;
  },
};

export const dashboardApi = {
  getSummary: async (): Promise<DashboardSummary> => {
    const { data } = await apiClient.get<DashboardSummary>('/dashboard/summary');
    return data;
  },
};

export const serversApi = {
  list: async (params?: {
    status?: string;
    search?: string;
    is_demo?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Server>> => {
    const { data } = await apiClient.get<PaginatedResponse<Server>>('/servers', { params });
    return data;
  },
  get: async (serverId: string): Promise<Server> => {
    const { data } = await apiClient.get<Server>(`/servers/${serverId}`);
    return data;
  },
  register: async (payload: {
    hostname: string;
    display_name?: string;
    ip_address?: string;
    os_name?: string;
    os_version?: string;
    cpu_cores?: number;
    tags?: string[];
  }): Promise<ServerRegisterResponse> => {
    const { data } = await apiClient.post<ServerRegisterResponse>('/servers/register', payload);
    return data;
  },
  rotateToken: async (serverId: string): Promise<{ server_id: string; api_token: string; token_prefix: string }> => {
    const { data } = await apiClient.post(`/servers/${serverId}/rotate-token`);
    return data;
  },
  remove: async (serverId: string): Promise<void> => {
    await apiClient.delete(`/servers/${serverId}`);
  },
  getLatestMetrics: async (serverId: string): Promise<ServerMetric | null> => {
    const { data } = await apiClient.get<ServerMetric | null>(`/servers/${serverId}/metrics`);
    return data;
  },
  getMetricsHistory: async (
    serverId: string,
    range: '15m' | '1h' | '6h' | '24h' | '7d' = '1h',
    limit = 200,
  ): Promise<ServerMetric[]> => {
    const { data } = await apiClient.get<ServerMetric[]>(`/servers/${serverId}/metrics/history`, {
      params: { range, limit },
    });
    return data;
  },
  getProcesses: async (
    serverId: string,
    params?: { search?: string; sort_by?: string; order?: string },
  ): Promise<ProcessListResponse> => {
    const { data } = await apiClient.get<ProcessListResponse>(`/servers/${serverId}/processes`, { params });
    return data;
  },
};

export const alertsApi = {
  list: async (params?: {
    severity?: string;
    status?: string;
    server_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Alert>> => {
    const { data } = await apiClient.get<PaginatedResponse<Alert>>('/alerts', { params });
    return data;
  },
  summary: async (): Promise<AlertSummary> => {
    const { data } = await apiClient.get<AlertSummary>('/alerts/summary');
    return data;
  },
  acknowledge: async (alertId: string): Promise<Alert> => {
    const { data } = await apiClient.patch<Alert>(`/alerts/${alertId}/acknowledge`);
    return data;
  },
  resolve: async (alertId: string): Promise<Alert> => {
    const { data } = await apiClient.patch<Alert>(`/alerts/${alertId}/resolve`);
    return data;
  },
};

export const logsApi = {
  search: async (params?: {
    q?: string;
    server_id?: string;
    severity?: string;
    source?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<SystemLog>> => {
    const endpoint = params?.q ? '/logs/search' : '/logs';
    const { data } = await apiClient.get<PaginatedResponse<SystemLog>>(endpoint, { params });
    return data;
  },
};

export const settingsApi = {
  get: async (): Promise<SystemSettings> => {
    const { data } = await apiClient.get<SystemSettings>('/settings');
    return data;
  },
  update: async (payload: Omit<SystemSettings, 'updated_at'>): Promise<SystemSettings> => {
    const { data } = await apiClient.put<SystemSettings>('/settings', payload);
    return data;
  },
};

