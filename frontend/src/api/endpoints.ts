import { api } from './client'

export interface Health { status: string; model_version: string; latest_data_timestamp: string; last_refresh: string | null }
export interface OverviewItem {
  city: string; lat: number; lon: number; pm25: number; category: string; color: string
  alert_24h: boolean; alert_score: number; pred_24h: number; pred_category_24h: string
  trend: 'better' | 'worse' | 'steady'; observed_at: string
}
export interface Current {
  city: string; observed_at: string; category: string; color: string; us_aqi: number | null
  pollutants: Record<string, number | null>; weather: Record<string, number | null>
}
export interface HistoryPoint { timestamp: string; pm25: number | null; pm10: number | null; no2: number | null }
export interface ForecastPoint { timestamp: string; hour_ahead: number; pm25: number; lower: number; upper: number; category: string }
export interface Forecast {
  city: string; generated_from: string; alert_24h: boolean; alert_score: number
  mean_24h: number; category_24h: string; points: ForecastPoint[]
}
export interface Factor { label: string; shap: number; direction: 'up' | 'down'; text: string }
export interface Explain { city: string; horizon_hours: number; base_value: number; factors: Factor[] }
export interface BestTime { city: string; start: string; end: string; mean_pm25: number; category: string; worst_start: string; worst_mean_pm25: number }
export interface Advisory { category: string; color: string; summary: string; groups: Record<string, string> }
export interface PerfRow { model: string; horizon: number; test: string; n_test: number; MAE: number; RMSE: number; R2: number; skill_vs_persistence: number }
export interface Performance {
  metadata: Record<string, any>
  table: PerfRow[]
  alert: { test: string; threshold: number; precision: number; recall: number; f1: number; pr_auc: number; roc_auc: number; base_rate: number }[]
}
export interface Importance { feature: string; importance: number }

const get = <T,>(url: string, params?: object) => api.get<T>(url, { params }).then((r) => r.data)

export const getHealth = () => get<Health>('/api/health')
export const getOverview = () => get<OverviewItem[]>('/api/overview')
export const getCurrent = (c: string) => get<Current>(`/api/cities/${c}/current`)
export const getHistory = (c: string, hours = 168) => get<HistoryPoint[]>(`/api/cities/${c}/history`, { hours })
export const getForecast = (c: string) => get<Forecast>(`/api/cities/${c}/forecast`)
export const getExplain = (c: string) => get<Explain>(`/api/cities/${c}/explain`)
export const getBestTime = (c: string) => get<BestTime>(`/api/cities/${c}/best-time`)
export const getCompare = (cities: string[]) => get<{ series: Record<string, ForecastPoint[]> }>('/api/compare', { cities: cities.join(',') })
export const getPerformance = () => get<Performance>('/api/model/performance')
export const getImportance = () => get<Importance[]>('/api/model/importance')
export const getAdvisory = (category: string) => get<Advisory>('/api/advisory', { category })
