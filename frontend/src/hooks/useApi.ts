import { useQuery } from '@tanstack/react-query'
import * as e from '@/api/endpoints'

const REFRESH = 10 * 60 * 1000
const opts = { refetchInterval: REFRESH, staleTime: 60_000 }

export const useHealth = () => useQuery({ queryKey: ['health'], queryFn: e.getHealth, ...opts })
export const useOverview = () => useQuery({ queryKey: ['overview'], queryFn: e.getOverview, ...opts })
export const useCurrent = (c: string) => useQuery({ queryKey: ['current', c], queryFn: () => e.getCurrent(c), ...opts })
export const useHistory = (c: string, hours = 168) => useQuery({ queryKey: ['history', c, hours], queryFn: () => e.getHistory(c, hours), ...opts })
export const useForecast = (c: string) => useQuery({ queryKey: ['forecast', c], queryFn: () => e.getForecast(c), ...opts })
export const useExplain = (c: string) => useQuery({ queryKey: ['explain', c], queryFn: () => e.getExplain(c), ...opts })
export const useBestTime = (c: string) => useQuery({ queryKey: ['best', c], queryFn: () => e.getBestTime(c), ...opts })
export const useCompare = (cities: string[]) =>
  useQuery({ queryKey: ['compare', cities], queryFn: () => e.getCompare(cities), enabled: cities.length > 0, ...opts })
export const usePerformance = () => useQuery({ queryKey: ['perf'], queryFn: e.getPerformance, staleTime: Infinity })
export const useImportance = () => useQuery({ queryKey: ['importance'], queryFn: e.getImportance, staleTime: Infinity })
export const useAdvisory = (cat: string) => useQuery({ queryKey: ['advisory', cat], queryFn: () => e.getAdvisory(cat), staleTime: Infinity })
