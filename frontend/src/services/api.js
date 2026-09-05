import axios from 'axios'

// Use relative /api path → Vite dev proxy handles forwarding to backend (no CORS).
// Set VITE_API_URL only when you want to point directly at a remote backend.
const BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response error interceptor
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Unknown error'
    console.error('API Error:', msg)
    return Promise.reject(new Error(msg))
  }
)

export const dashboardApi = {
  getSummary: () => api.get('/dashboard/summary'),
}

export const opportunitiesApi = {
  list: (params = {}) => api.get('/opportunities', { params }),
  get: (paymentId) => api.get(`/opportunities/${paymentId}`),
}

export const recoveryApi = {
  analyze: (paymentId) => api.post(`/recovery/${paymentId}/analyze`),
  execute: (paymentId) => api.post(`/recovery/${paymentId}/execute`),
}

export const auditApi = {
  getLogs: (params = {}) => api.get('/audit', { params }),
}

export const policiesApi = {
  get: () => api.get('/policies'),
  update: (data) => api.put('/policies', data),
}

export const evaluationApi = {
  get: () => api.get('/evaluation'),
}

export const demoApi = {
  listScenarios: () => api.get('/demo/scenarios'),
  runScenario: (scenarioId) => api.post('/demo/scenario', { scenario_id: scenarioId }),
}

export const healthApi = {
  check: () => api.get('/health'),
}

export default api
