import React, { useState, useEffect } from 'react'
import { Play, RefreshCw, AlertTriangle, Check, Clock, XCircle, Database, MapPin, Calendar } from 'lucide-react'

// Types
interface ScrapeJob {
  id: string
  state: string
  county: string | null
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  items_found: number
  items_added: number
  items_updated: number
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  triggered_by: string | null
  created_at: string | null
  duration_seconds?: number
}

interface ScrapeJobsResponse {
  jobs: ScrapeJob[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
}

interface DataFreshness {
  state: string
  county: string | null
  last_scrape: string | null
  last_scrape_status: string | null
  properties_count: number
  oldest_property: string | null
  newest_property: string | null
  freshness_score: number
}

interface StateFreshnessResponse {
  states: DataFreshness[]
}

interface AvailableState {
  state_code: string
  state_name: string
  is_active: boolean
  sale_type: string
  scraper_module: string
}

const STATUS_STYLES: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  pending: { bg: 'bg-warning/10', text: 'text-warning', icon: <Clock className="w-4 h-4" /> },
  running: { bg: 'bg-primary/10', text: 'text-primary', icon: <RefreshCw className="w-4 h-4 animate-spin" /> },
  completed: { bg: 'bg-success/10', text: 'text-success', icon: <Check className="w-4 h-4" /> },
  failed: { bg: 'bg-danger/10', text: 'text-danger', icon: <XCircle className="w-4 h-4" /> },
  cancelled: { bg: 'bg-neutral-1', text: 'text-text-muted', icon: <XCircle className="w-4 h-4" /> },
}

export function ScrapeJobs() {
  const [jobs, setJobs] = useState<ScrapeJobsResponse | null>(null)
  const [freshness, setFreshness] = useState<StateFreshnessResponse | null>(null)
  const [availableStates, setAvailableStates] = useState<AvailableState[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Trigger scrape state
  const [selectedState, setSelectedState] = useState<string>('')
  const [isTriggering, setIsTriggering] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setIsLoading(true)
      await Promise.all([
        fetchJobs(),
        fetchFreshness(),
        fetchAvailableStates()
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchJobs = async () => {
    const response = await fetch('/api/v1/scrape/jobs?page_size=20', {
      headers: {
        'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
      }
    })
    if (!response.ok) throw new Error('Failed to load jobs')
    const data: ScrapeJobsResponse = await response.json()
    setJobs(data)
  }

  const fetchFreshness = async () => {
    const response = await fetch('/api/v1/scrape/freshness', {
      headers: {
        'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
      }
    })
    if (!response.ok) throw new Error('Failed to load freshness')
    const data: StateFreshnessResponse = await response.json()
    setFreshness(data)
  }

  const fetchAvailableStates = async () => {
    const response = await fetch('/api/v1/scrape/states', {
      headers: {
        'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
      }
    })
    if (!response.ok) throw new Error('Failed to load states')
    const data = await response.json()
    setAvailableStates(data.states || [])
  }

  const triggerScrape = async () => {
    if (!selectedState) return

    try {
      setIsTriggering(true)
      setError(null)
      setSuccess(null)

      const response = await fetch('/api/v1/scrape/trigger', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
        },
        body: JSON.stringify({
          state: selectedState,
          county: null
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to trigger scrape')
      }

      setSuccess(`Scrape job started for ${selectedState}`)
      setSelectedState('')

      // Refresh jobs list
      await fetchJobs()

      // Clear success after 5 seconds
      setTimeout(() => setSuccess(null), 5000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to trigger scrape')
    } finally {
      setIsTriggering(false)
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const formatDuration = (seconds: number | undefined) => {
    if (!seconds) return '-'
    if (seconds < 60) return `${Math.round(seconds)}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    return `${Math.round(seconds / 3600)}h`
  }

  const getFreshnessColor = (score: number) => {
    if (score >= 80) return 'text-success'
    if (score >= 50) return 'text-warning'
    return 'text-danger'
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-text-primary mb-2">Scrape Jobs</h1>
          <p className="text-text-muted">Monitor and trigger data scraping</p>
        </div>
        <div className="animate-pulse space-y-6">
          <div className="bg-card rounded-lg p-6 border border-neutral-1 h-32"></div>
          <div className="bg-card rounded-lg p-6 border border-neutral-1 h-64"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Scrape Jobs</h1>
        <p className="text-text-muted">Monitor and trigger data scraping</p>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="mb-6 p-4 bg-danger/10 border border-danger/20 rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-danger" />
          <p className="text-danger text-sm">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto text-danger hover:text-danger/80">
            Dismiss
          </button>
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 bg-success/10 border border-success/20 rounded-lg flex items-center gap-2">
          <Check className="w-5 h-5 text-success" />
          <p className="text-success text-sm">{success}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Data Freshness & Trigger */}
        <div className="space-y-6">
          {/* Trigger New Scrape */}
          <div className="bg-card rounded-lg p-6 border border-neutral-1">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Trigger Scrape</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-text-muted mb-1">State</label>
                <select
                  value={selectedState}
                  onChange={e => setSelectedState(e.target.value)}
                  className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary focus:outline-none focus:border-primary"
                >
                  <option value="">Select state...</option>
                  {availableStates.filter(s => s.is_active).map(state => (
                    <option key={state.state_code} value={state.state_code}>
                      {state.state_name} ({state.state_code})
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={triggerScrape}
                disabled={!selectedState || isTriggering}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
              >
                {isTriggering ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    Start Scrape
                  </>
                )}
              </button>

              {availableStates.filter(s => !s.is_active).length > 0 && (
                <p className="text-xs text-text-muted">
                  Inactive states: {availableStates.filter(s => !s.is_active).map(s => s.state_code).join(', ')}
                </p>
              )}
            </div>
          </div>

          {/* Data Freshness */}
          <div className="bg-card rounded-lg p-6 border border-neutral-1">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-text-primary">Data Freshness</h2>
              <button
                onClick={fetchFreshness}
                className="p-1 text-text-muted hover:text-primary"
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {freshness && (
              <div className="space-y-3">
                {freshness.states.map(state => (
                  <div key={state.state} className="p-3 bg-surface rounded-lg">
                    <div className="flex justify-between items-center mb-2">
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-text-muted" />
                        <span className="font-medium text-text-primary">{state.state}</span>
                      </div>
                      <span className={`text-lg font-bold ${getFreshnessColor(state.freshness_score)}`}>
                        {state.freshness_score.toFixed(0)}%
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-text-muted">Properties:</span>
                        <span className="ml-1 text-text-primary">{state.properties_count.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-text-muted">Last scrape:</span>
                        <span className="ml-1 text-text-primary">
                          {state.last_scrape ? new Date(state.last_scrape).toLocaleDateString() : 'Never'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Job History */}
        <div className="lg:col-span-2">
          <div className="bg-card rounded-lg border border-neutral-1">
            <div className="p-4 border-b border-neutral-1 flex justify-between items-center">
              <h2 className="text-lg font-semibold text-text-primary">Job History</h2>
              <button
                onClick={fetchJobs}
                className="flex items-center gap-1 text-sm text-text-muted hover:text-primary"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>

            {jobs && jobs.jobs.length === 0 ? (
              <div className="p-12 text-center">
                <Database className="w-12 h-12 text-text-muted mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-text-primary mb-2">No scrape jobs yet</h3>
                <p className="text-text-muted">
                  Trigger a scrape to start collecting property data.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-neutral-1">
                {jobs?.jobs.map(job => {
                  const statusStyle = STATUS_STYLES[job.status] || STATUS_STYLES.pending

                  return (
                    <div key={job.id} className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-text-primary">
                              {job.state}{job.county ? ` - ${job.county}` : ' (All counties)'}
                            </span>
                            <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${statusStyle.bg} ${statusStyle.text}`}>
                              {statusStyle.icon}
                              {job.status}
                            </span>
                          </div>
                          <div className="flex items-center gap-1 text-xs text-text-muted mt-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(job.created_at)}
                          </div>
                        </div>

                        {job.status === 'completed' && (
                          <div className="text-right">
                            <p className="text-sm font-medium text-text-primary">
                              {job.items_found.toLocaleString()} found
                            </p>
                            <p className="text-xs text-text-muted">
                              +{job.items_added} new, {job.items_updated} updated
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Progress info for running jobs */}
                      {job.status === 'running' && (
                        <div className="mt-2">
                          <div className="h-2 bg-surface rounded-full overflow-hidden">
                            <div className="h-full bg-primary animate-pulse" style={{ width: '50%' }}></div>
                          </div>
                          <p className="text-xs text-text-muted mt-1">
                            {job.items_found} properties found so far...
                          </p>
                        </div>
                      )}

                      {/* Error message for failed jobs */}
                      {job.status === 'failed' && job.error_message && (
                        <div className="mt-2 p-2 bg-danger/5 rounded text-xs text-danger">
                          {job.error_message}
                        </div>
                      )}

                      {/* Duration for completed jobs */}
                      {job.duration_seconds && (
                        <p className="text-xs text-text-muted mt-2">
                          Duration: {formatDuration(job.duration_seconds)}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {/* Pagination */}
            {jobs && jobs.total_pages > 1 && (
              <div className="p-4 border-t border-neutral-1 text-center text-sm text-text-muted">
                Page {jobs.page} of {jobs.total_pages} ({jobs.total_count} total jobs)
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
