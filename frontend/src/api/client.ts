import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  timeout: 30000,
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const detail = err.response?.data?.detail ?? err.message ?? 'Request failed'
    return Promise.reject(new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)))
  },
)
