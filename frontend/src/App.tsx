import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import Navbar from '@/components/layout/Navbar'
import Footer from '@/components/layout/Footer'
import Dashboard from '@/pages/Dashboard'
import { Skeleton } from '@/components/common/ui'

const CityDetail = lazy(() => import('@/pages/CityDetail'))
const Compare = lazy(() => import('@/pages/Compare'))
const ModelInsights = lazy(() => import('@/pages/ModelInsights'))
const About = lazy(() => import('@/pages/About'))

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })

const TITLES: Record<string, string> = { '/': 'Dashboard', '/compare': 'Compare cities', '/model': 'Model insights', '/about': 'About' }

function Titles() {
  const { pathname } = useLocation()
  useEffect(() => {
    const t = pathname.startsWith('/city/') ? decodeURIComponent(pathname.slice(6)) : TITLES[pathname] ?? 'AirCast India'
    document.title = `${t} · AirCast India`
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Titles />
        <Navbar />
        <Suspense fallback={<div className="mx-auto mt-10 max-w-6xl px-4"><Skeleton className="h-96" /></div>}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/city/:name" element={<CityDetail />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/model" element={<ModelInsights />} />
            <Route path="/about" element={<About />} />
            <Route path="*" element={<p className="py-20 text-center text-muted">Page not found.</p>} />
          </Routes>
        </Suspense>
        <Footer />
        <Toaster position="bottom-right" richColors />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
