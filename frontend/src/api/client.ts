import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
};

export const employeesAPI = {
  list: (params?: Record<string, any>) => api.get('/employees', { params }),
  get: (id: number) => api.get(`/employees/${id}`),
  create: (data: any) => api.post('/employees', data),
  update: (id: number, data: any) => api.put(`/employees/${id}`, data),
  delete: (id: number) => api.delete(`/employees/${id}`),
  byCompany: (companyId: number) => api.get(`/employees?company_id=${companyId}`),
};

export const attendanceAPI = {
  list: (params?: Record<string, any>) => api.get('/attendance', { params }),
  add: (data: any) => api.post('/attendance', data),
  update: (id: number, data: any) => api.put(`/attendance/${id}`, data),
  delete: (id: number) => api.delete(`/attendance/${id}`),
  bulkSave: (data: any) => api.post('/attendance/bulk', data),
};

export const companiesAPI = {
  list: () => api.get('/companies'),
  get: (id: number) => api.get(`/companies/${id}`),
  create: (data: any) => api.post('/companies', data),
  update: (id: number, data: any) => api.put(`/companies/${id}`, data),
  delete: (id: number) => api.delete(`/companies/${id}`),
  regions: (companyId: number) => api.get(`/companies/${companyId}/regions`),
  locations: (regionId: number) => api.get(`/regions/${regionId}/locations`),
};

export const evaluationsAPI = {
  list: (params?: Record<string, any>) => api.get('/evaluations', { params }),
  create: (data: any) => api.post('/evaluations', data),
  criteria: () => api.get('/evaluation-criteria'),
  areas: () => api.get('/evaluations/areas'),
};

export const financialAPI = {
  dashboard: () => api.get('/financial/dashboard'),
  salaries: (params?: Record<string, any>) => api.get('/financial/salaries', { params }),
  salaryCalculation: (data: any) => api.post('/financial/salary-calculation', data),
  transactions: (params?: Record<string, any>) => api.get('/financial/transactions', { params }),
  createTransaction: (data: any) => api.post('/financial/transactions', data),
};

export const accountsAPI = {
  dashboard: () => api.get('/accounts'),
  chart: () => api.get('/accounts/chart'),
  add: (data: any) => api.post('/accounts', data),
  update: (id: number, data: any) => api.put(`/accounts/${id}`, data),
  delete: (id: number) => api.delete(`/accounts/${id}`),
  journal: (params?: Record<string, any>) => api.get('/accounts/journal', { params }),
  addJournalEntry: (data: any) => api.post('/accounts/journal', data),
  trialBalance: () => api.get('/accounts/trial-balance'),
  incomeStatement: () => api.get('/accounts/income-statement'),
  balanceSheet: () => api.get('/accounts/balance-sheet'),
};

export const suppliersAPI = {
  list: () => api.get('/suppliers'),
  create: (data: any) => api.post('/suppliers', data),
  update: (id: number, data: any) => api.put(`/suppliers/${id}`, data),
  delete: (id: number) => api.delete(`/suppliers/${id}`),
  invoices: (params?: Record<string, any>) => api.get('/supplier-invoices', { params }),
};

export const reportsAPI = {
  dashboard: () => api.get('/reports/dashboard'),
  attendance: (params?: Record<string, any>) => api.get('/reports/attendance', { params }),
  financial: (params?: Record<string, any>) => api.get('/reports/financial', { params }),
  employees: () => api.get('/reports/employees'),
};

export const dashboardAPI = {
  stats: () => api.get('/dashboard/stats'),
};

export default api;
