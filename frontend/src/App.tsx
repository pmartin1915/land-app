import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AppProvider } from './lib/context'
import { ThemeProvider } from './lib/theme-provider'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Parcels } from './pages/Parcels'
import { Map } from './pages/Map'
import { Triage } from './pages/Triage'
import { ScrapeJobs } from './pages/ScrapeJobs'
import { Watchlist } from './pages/Watchlist'
import { Reports } from './pages/Reports'
import { Settings } from './pages/Settings'

function App() {
  return (
    <ThemeProvider defaultTheme="dark">
      <AppProvider>
        <Router>
          <div className="app min-h-screen bg-bg text-text-primary font-inter antialiased">
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/parcels" element={<Parcels />} />
                <Route path="/map" element={<Map />} />
                <Route path="/triage" element={<Triage />} />
                <Route path="/scrape-jobs" element={<ScrapeJobs />} />
                <Route path="/watchlist" element={<Watchlist />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Layout>
          </div>
        </Router>
      </AppProvider>
    </ThemeProvider>
  )
}

export default App