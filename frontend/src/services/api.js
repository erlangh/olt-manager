import axios from 'axios';
import { message } from 'antd';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors and token refresh
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
          const response = await axios.post(
            `${process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1'}/auth/refresh`,
            { refresh_token: refreshToken }
          );

          const { access_token, refresh_token: newRefreshToken } = response.data;
          
          localStorage.setItem('token', access_token);
          localStorage.setItem('refreshToken', newRefreshToken);
          
          // Update authorization header
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          originalRequest.headers.Authorization = `Bearer ${access_token}`;

          return api(originalRequest);
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
        
        // Clear tokens and redirect to login
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        delete api.defaults.headers.common['Authorization'];
        
        // Redirect to login page
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    // Handle other HTTP errors
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          message.error(data.detail || 'Bad request');
          break;
        case 403:
          message.error('Access denied. You do not have permission to perform this action.');
          break;
        case 404:
          message.error('Resource not found');
          break;
        case 422:
          // Validation errors
          if (data.detail && Array.isArray(data.detail)) {
            const errorMessages = data.detail.map(err => `${err.loc?.join('.')}: ${err.msg}`);
            message.error(errorMessages.join(', '));
          } else {
            message.error(data.detail || 'Validation error');
          }
          break;
        case 429:
          message.error('Too many requests. Please try again later.');
          break;
        case 500:
          message.error('Internal server error. Please try again later.');
          break;
        case 502:
        case 503:
        case 504:
          message.error('Service temporarily unavailable. Please try again later.');
          break;
        default:
          message.error(data.detail || `HTTP Error ${status}`);
      }
    } else if (error.request) {
      // Network error
      message.error('Network error. Please check your connection and try again.');
    } else {
      // Other errors
      message.error('An unexpected error occurred');
    }

    return Promise.reject(error);
  }
);

// API service methods
export const apiService = {
  // Authentication
  auth: {
    login: (credentials) => api.post('/auth/login', credentials),
    register: (userData) => api.post('/auth/register', userData),
    refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
    me: () => api.get('/auth/me'),
    changePassword: (passwordData) => api.post('/auth/change-password', passwordData),
    updateProfile: (profileData) => api.put('/auth/profile', profileData),
  },

  // OLT Management
  olt: {
    list: (params) => api.get('/olt/', { params }),
    get: (id) => api.get(`/olt/${id}`),
    create: (data) => api.post('/olt/', data),
    update: (id, data) => api.put(`/olt/${id}`, data),
    delete: (id) => api.delete(`/olt/${id}`),
    systemInfo: (id) => api.get(`/olt/${id}/system-info`),
    performance: (id, params) => api.get(`/olt/${id}/performance`, { params }),
    ports: (id) => api.get(`/olt/${id}/ports`),
    testConnection: (id) => api.post(`/olt/${id}/test-connection`),
  },

  // ONT Management
  ont: {
    list: (params) => api.get('/ont/', { params }),
    get: (id) => api.get(`/ont/${id}`),
    create: (data) => api.post('/ont/', data),
    update: (id, data) => api.put(`/ont/${id}`, data),
    delete: (id) => api.delete(`/ont/${id}`),
    provision: (data) => api.post('/ont/provision', data),
    bulkProvision: (data) => api.post('/ont/bulk-provision', data),
    bulkDelete: (data) => api.post('/ont/bulk-delete', data),
    discover: (oltId) => api.post(`/ont/discover/${oltId}`),
    services: (id) => api.get(`/ont/${id}/services`),
    addService: (id, data) => api.post(`/ont/${id}/services`, data),
    updateService: (id, serviceId, data) => api.put(`/ont/${id}/services/${serviceId}`, data),
    deleteService: (id, serviceId) => api.delete(`/ont/${id}/services/${serviceId}`),
  },

  // Monitoring
  monitoring: {
    dashboard: () => api.get('/monitoring/dashboard'),
    alarms: (params) => api.get('/monitoring/alarms', { params }),
    acknowledgeAlarm: (id) => api.post(`/monitoring/alarms/${id}/acknowledge`),
    performance: (params) => api.get('/monitoring/performance', { params }),
    realTimePerformance: (params) => api.get('/monitoring/performance/realtime', { params }),
    chartData: (params) => api.get('/monitoring/performance/chart', { params }),
    createTestAlarm: (data) => api.post('/monitoring/test-alarm', data),
    health: () => api.get('/monitoring/health'),
    cleanup: () => api.post('/monitoring/cleanup'),
  },

  // Configuration
  configuration: {
    list: (params) => api.get('/configuration/', { params }),
    get: (id) => api.get(`/configuration/${id}`),
    create: (data) => api.post('/configuration/', data),
    update: (id, data) => api.put(`/configuration/${id}`, data),
    delete: (id) => api.delete(`/configuration/${id}`),
    apply: (id, oltId) => api.post(`/configuration/${id}/apply/${oltId}`),
    backup: (oltId) => api.post(`/configuration/backup/${oltId}`),
    restore: (oltId, backupId) => api.post(`/configuration/restore/${oltId}/${backupId}`),
    serviceProfiles: (params) => api.get('/configuration/service-profiles', { params }),
    createServiceProfile: (data) => api.post('/configuration/service-profiles', data),
    updateServiceProfile: (id, data) => api.put(`/configuration/service-profiles/${id}`, data),
    deleteServiceProfile: (id) => api.delete(`/configuration/service-profiles/${id}`),
  },

  // User Management
  users: {
    list: (params) => api.get('/users/', { params }),
    get: (id) => api.get(`/users/${id}`),
    create: (data) => api.post('/users/', data),
    update: (id, data) => api.put(`/users/${id}`, data),
    delete: (id) => api.delete(`/users/${id}`),
    changePassword: (id, data) => api.post(`/users/${id}/change-password`, data),
    resetPassword: (id) => api.post(`/users/${id}/reset-password`),
    activate: (id) => api.post(`/users/${id}/activate`),
    deactivate: (id) => api.post(`/users/${id}/deactivate`),
    stats: () => api.get('/users/stats'),
    profile: (id) => api.get(`/users/${id}/profile`),
  },

  // Reports
  reports: {
    oltSummary: (params) => api.get('/reports/olt-summary', { params }),
    ontStatus: (params) => api.get('/reports/ont-status', { params }),
    alarms: (params) => api.get('/reports/alarms', { params }),
    performance: (params) => api.get('/reports/performance', { params }),
    userActivity: (params) => api.get('/reports/user-activity', { params }),
    analytics: () => api.get('/reports/analytics'),
    exportChart: (data) => api.post('/reports/export-chart', data, { responseType: 'blob' }),
  },

  // File uploads
  upload: {
    file: (file, onProgress) => {
      const formData = new FormData();
      formData.append('file', file);
      
      return api.post('/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(percentCompleted);
          }
        },
      });
    },
  },

  // Utility methods
  utils: {
    ping: (host) => api.post('/utils/ping', { host }),
    traceroute: (host) => api.post('/utils/traceroute', { host }),
    nslookup: (host) => api.post('/utils/nslookup', { host }),
  },
};

// Export default axios instance for direct use
export default api;