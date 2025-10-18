import axios from 'axios';

// API 基础 URL
const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8080';

// 创建 axios 实例
export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // 提取错误信息：优先使用后端返回的 detail
    const message = error.response?.data?.detail ||
                    error.response?.data?.message ||
                    error.message ||
                    '请求失败';

    // 保留原始 error 对象，以便前端可以访问 response
    const enhancedError: any = new Error(message);
    enhancedError.response = error.response;
    enhancedError.status = error.response?.status;

    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      message: message,
      detail: error.response?.data
    });

    return Promise.reject(enhancedError);
  }
);

// API 响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  timestamp: string;
}

// 导出 API 方法
export const api = {
  // Dashboard API
  dashboard: {
    getSummary: () => apiClient.get<ApiResponse>('/api/dashboard/summary'),
    getActivity: () => apiClient.get<ApiResponse>('/api/dashboard/activity'),
  },

  // Configs API
  configs: {
    list: () => apiClient.get<ApiResponse>('/api/configs'),
    get: (name: string) => apiClient.get<ApiResponse>(`/api/configs/${name}`),
    getDefault: () => apiClient.get<ApiResponse>('/api/configs/default'),
    getCurrent: () => apiClient.get<ApiResponse>('/api/configs/current'),
    create: (data: any) => apiClient.post<ApiResponse>('/api/configs', data),
    update: (name: string, data: any) => apiClient.put<ApiResponse>(`/api/configs/${name}`, data),
    delete: (name: string) => apiClient.delete<ApiResponse>(`/api/configs/${name}`),
    use: (name: string) => apiClient.post<ApiResponse>(`/api/configs/${name}/use`),
    setDefault: (name: string) => apiClient.post<ApiResponse>(`/api/configs/${name}/default`),
    sync: () => apiClient.post<ApiResponse>('/api/configs/sync'),
  },

  // EndpointGroups API (高可用代理组)
  endpoints: {
    // CRUD 操作
    list: () => apiClient.get<ApiResponse>('/api/endpoints'),
    get: (name: string) => apiClient.get<ApiResponse>(`/api/endpoints/${name}`),
    create: (data: any) => apiClient.post<ApiResponse>('/api/endpoints', data),
    update: (name: string, data: any) => apiClient.put<ApiResponse>(`/api/endpoints/${name}`, data),
    delete: (name: string) => apiClient.delete<ApiResponse>(`/api/endpoints/${name}`),

    // 主节点管理
    addPrimary: (name: string, config_name: string) =>
      apiClient.post<ApiResponse>(`/api/endpoints/${name}/primary`, { config_name }),
    removePrimary: (name: string, config_name: string) =>
      apiClient.delete<ApiResponse>(`/api/endpoints/${name}/primary/${config_name}`),

    // 副节点管理
    addSecondary: (name: string, config_name: string) =>
      apiClient.post<ApiResponse>(`/api/endpoints/${name}/secondary`, { config_name }),
    removeSecondary: (name: string, config_name: string) =>
      apiClient.delete<ApiResponse>(`/api/endpoints/${name}/secondary/${config_name}`),
  },

  // Proxy API
  proxy: {
    status: () => apiClient.get<ApiResponse>('/api/proxy/status'),
    start: (data: any) => apiClient.post<ApiResponse>('/api/proxy/start', data),
    stop: () => apiClient.post<ApiResponse>('/api/proxy/stop'),
    logs: (params?: { lines?: number; level?: string; grep?: string }) =>
      apiClient.get<ApiResponse>('/api/proxy/logs', { params }),
  },

  // Health API
  health: {
    status: () => apiClient.get<ApiResponse>('/api/health/status'),
    test: () => apiClient.post<ApiResponse>('/api/health/test'),
    metrics: () => apiClient.get<ApiResponse>('/api/health/metrics'),
    runtime: () => apiClient.get<ApiResponse>('/api/health/runtime'),
    moveNode: (data: { config_name: string; to_type: string }) =>
      apiClient.post<ApiResponse>('/api/health/runtime/move-node', data),
    addNode: (data: { config_name: string; node_type: string }) =>
      apiClient.post<ApiResponse>('/api/health/runtime/add-node', data),
    removeNode: (data: { config_name: string }) =>
      apiClient.post<ApiResponse>('/api/health/runtime/remove-node', data),
  },

  // Queue API
  queue: {
    status: () => apiClient.get<ApiResponse>('/api/queue/status'),
    items: () => apiClient.get<ApiResponse>('/api/queue/items'),
    retryAll: () => apiClient.post<ApiResponse>('/api/queue/retry-all'),
    clear: () => apiClient.post<ApiResponse>('/api/queue/clear'),
  },

  // Priority API
  priority: {
    get: () => apiClient.get<ApiResponse>('/api/priority'),
    history: () => apiClient.get<ApiResponse>('/api/priority/history'),
  },

  // Claude Config API
  claudeConfig: {
    status: () => apiClient.get<ApiResponse>('/api/claude-config/status'),
    apply: (data?: { proxy_url?: string; api_key?: string }) =>
      apiClient.post<ApiResponse>('/api/claude-config/apply', null, { params: data }),
    restore: () => apiClient.post<ApiResponse>('/api/claude-config/restore'),
  },
};
