// API 响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  timestamp: string;
}

// Dashboard 类型
export interface DashboardSummary {
  total_configs: number;
  active_config: string | null;
  storage_backend: string;
  proxy_status: ProxyStatus;
  endpoint_health: EndpointHealth;
}

export interface ProxyStatus {
  running: boolean;
  pid?: number;
  host?: string;
  port?: number;
  uptime?: number;
  config?: string;
}

export interface EndpointHealth {
  healthy: number;
  warning: number;
  failed: number;
}

// Config 类型
export interface Config {
  name: string;
  description?: string;
  base_url?: string;
  api_key?: string;
  endpoints?: any[];
  is_default: boolean;
  priority_level?: string;
  enabled: boolean;
  last_used?: string;
}
