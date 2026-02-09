import React, { Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppProvider } from './lib/context'
import { ThemeProvider } from './lib/theme-provider'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import { RouteErrorBoundary } from './components/ui/RouteErrorBoundary'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Toaster } from './components/ui/Toast'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000, // 2 minutes before data is considered stale
      gcTime: 10 * 60 * 1000, // 10 minutes before unused data is garbage collected
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Lazy-loaded pages -- only downloaded when navigated to
const Parcels = React.lazy(() => import('./pages/Parcels').then(m => ({ default: m.Parcels })))
const Map = React.lazy(() => import('./pages/Map').then(m => ({ default: m.Map })))
const Triage = React.lazy(() => import('./pages/Triage').then(m => ({ default: m.Triage })))
const ScrapeJobs = React.lazy(() => import('./pages/ScrapeJobs').then(m => ({ default: m.ScrapeJobs })))
const Watchlist = React.lazy(() => import('./pages/Watchlist').then(m => ({ default: m.Watchlist })))
const Reports = React.lazy(() => import('./pages/Reports').then(m => ({ default: m.Reports })))
const Settings = React.lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })))
const MyFirstDeal = React.lazy(() => import('./pages/MyFirstDeal').then(m => ({ default: m.MyFirstDeal })))
const Portfolio = React.lazy(() => import('./pages/Portfolio').then(m => ({ default: m.Portfolio })))

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-text-muted">Loading...</div>
    </div>
  )
}

/**
 * Wrapper component that provides route-level error boundary and Suspense.
 * If a page crashes, only that page shows an error - navigation still works.
 */
function RouteWrapper({ children, name }: { children: React.ReactNode; name: string }) {
  return (
    <RouteErrorBoundary routeName={name}>
      <Suspense fallback={<LoadingFallback />}>
        {children}
      </Suspense>
    </RouteErrorBoundary>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark">
      <AppProvider>
        <Router>
          <div className="app min-h-screen bg-bg text-text-primary font-inter antialiased">
            <Layout>
              <Routes>
                <Route path="/" element={<RouteWrapper name="Dashboard"><Dashboard /></RouteWrapper>} />
                <Route path="/dashboard" element={<RouteWrapper name="Dashboard"><Dashboard /></RouteWrapper>} />
                <Route path="/parcels" element={<RouteWrapper name="Parcels"><Parcels /></RouteWrapper>} />
                <Route path="/map" element={<RouteWrapper name="Map"><Map /></RouteWrapper>} />
                <Route path="/triage" element={<RouteWrapper name="Triage"><Triage /></RouteWrapper>} />
                <Route path="/scrape-jobs" element={<RouteWrapper name="ScrapeJobs"><ScrapeJobs /></RouteWrapper>} />
                <Route path="/watchlist" element={<RouteWrapper name="Watchlist"><Watchlist /></RouteWrapper>} />
                <Route path="/my-first-deal" element={<RouteWrapper name="MyFirstDeal"><MyFirstDeal /></RouteWrapper>} />
                <Route path="/portfolio" element={<RouteWrapper name="Portfolio"><Portfolio /></RouteWrapper>} />
                <Route path="/reports" element={<RouteWrapper name="Reports"><Reports /></RouteWrapper>} />
                <Route path="/settings" element={<RouteWrapper name="Settings"><Settings /></RouteWrapper>} />
              </Routes>
            </Layout>
            <Toaster />
          </div>
        </Router>
      </AppProvider>
      </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
