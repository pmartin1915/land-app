import React, { useState } from 'react'
import { Download, FileJson, FileSpreadsheet, AlertTriangle, Check, RefreshCw, Eye } from 'lucide-react'

// Types
interface ExportPreview {
  total_matching: number
  sample_count: number
  sample: any[]
  filters_applied: {
    state: string | null
    county: string | null
    min_price: number | null
    max_price: number | null
    min_investment_score: number | null
    exclude_delta_region: boolean
    exclude_market_rejects: boolean
  }
}

// Available columns for export
const AVAILABLE_COLUMNS = [
  { key: 'parcel_id', label: 'Parcel ID', default: true },
  { key: 'state', label: 'State', default: true },
  { key: 'county', label: 'County', default: true },
  { key: 'amount', label: 'Price', default: true },
  { key: 'acreage', label: 'Acreage', default: true },
  { key: 'price_per_acre', label: 'Price/Acre', default: true },
  { key: 'investment_score', label: 'Investment Score', default: true },
  { key: 'buy_hold_score', label: 'Buy & Hold Score', default: true },
  { key: 'wholesale_score', label: 'Wholesale Score', default: true },
  { key: 'water_score', label: 'Water Score', default: false },
  { key: 'road_access_score', label: 'Road Access', default: false },
  { key: 'county_market_score', label: 'County Market', default: false },
  { key: 'description', label: 'Description', default: true },
  { key: 'owner_name', label: 'Owner', default: false },
  { key: 'year_sold', label: 'Year Sold', default: false },
  { key: 'status', label: 'Status', default: true },
  { key: 'sale_type', label: 'Sale Type', default: false },
  { key: 'redemption_period_days', label: 'Redemption Days', default: false },
  { key: 'assessed_value', label: 'Assessed Value', default: false },
  { key: 'created_at', label: 'Added Date', default: true },
]

export function Reports() {
  // Filter state
  const [state, setState] = useState<string>('')
  const [county, setCounty] = useState<string>('')
  const [minPrice, setMinPrice] = useState<string>('')
  const [maxPrice, setMaxPrice] = useState<string>('')
  const [minScore, setMinScore] = useState<string>('')
  const [excludeDelta, setExcludeDelta] = useState(false)
  const [excludeRejects, setExcludeRejects] = useState(true)

  // Column selection
  const [selectedColumns, setSelectedColumns] = useState<string[]>(
    AVAILABLE_COLUMNS.filter(c => c.default).map(c => c.key)
  )

  // UI state
  const [preview, setPreview] = useState<ExportPreview | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const fetchPreview = async () => {
    try {
      setIsLoadingPreview(true)
      setError(null)

      const params = new URLSearchParams()
      if (state) params.append('state', state)
      if (county) params.append('county', county)
      if (minPrice) params.append('min_price', minPrice)
      if (maxPrice) params.append('max_price', maxPrice)
      if (minScore) params.append('min_investment_score', minScore)
      if (excludeDelta) params.append('exclude_delta_region', 'true')
      if (excludeRejects) params.append('exclude_market_rejects', 'true')

      const response = await fetch(`/api/v1/export/preview?${params.toString()}`, {
        headers: {
          'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
        }
      })

      if (!response.ok) throw new Error('Failed to load preview')

      const data: ExportPreview = await response.json()
      setPreview(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview')
    } finally {
      setIsLoadingPreview(false)
    }
  }

  const exportData = async (format: 'csv' | 'json') => {
    try {
      setIsExporting(true)
      setError(null)
      setSuccess(null)

      const response = await fetch(`/api/v1/export/${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
        },
        body: JSON.stringify({
          columns: selectedColumns,
          state: state || null,
          county: county || null,
          min_price: minPrice ? parseFloat(minPrice) : null,
          max_price: maxPrice ? parseFloat(maxPrice) : null,
          min_investment_score: minScore ? parseFloat(minScore) : null,
          exclude_delta_region: excludeDelta,
          exclude_market_rejects: excludeRejects,
          max_results: 10000
        })
      })

      if (!response.ok) throw new Error('Export failed')

      // Get filename from header or generate one
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `auction_export.${format}`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=([^;]+)/)
        if (match) filename = match[1]
      }

      // Download the file
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      const totalCount = response.headers.get('X-Total-Count') || 'unknown'
      setSuccess(`Exported ${totalCount} properties to ${format.toUpperCase()}`)

      // Clear success after 5 seconds
      setTimeout(() => setSuccess(null), 5000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setIsExporting(false)
    }
  }

  const toggleColumn = (key: string) => {
    setSelectedColumns(prev =>
      prev.includes(key)
        ? prev.filter(c => c !== key)
        : [...prev, key]
    )
  }

  const selectAllColumns = () => {
    setSelectedColumns(AVAILABLE_COLUMNS.map(c => c.key))
  }

  const selectDefaultColumns = () => {
    setSelectedColumns(AVAILABLE_COLUMNS.filter(c => c.default).map(c => c.key))
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Reports / Exports</h1>
        <p className="text-text-muted">Export filtered property data to CSV or JSON</p>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="mb-6 p-4 bg-danger/10 border border-danger/20 rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-danger" />
          <p className="text-danger text-sm">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 bg-success/10 border border-success/20 rounded-lg flex items-center gap-2">
          <Check className="w-5 h-5 text-success" />
          <p className="text-success text-sm">{success}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Filters Section */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card rounded-lg p-6 border border-neutral-1">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Filters</h2>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {/* State */}
              <div>
                <label className="block text-sm text-text-muted mb-1">State</label>
                <select
                  value={state}
                  onChange={e => setState(e.target.value)}
                  className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary focus:outline-none focus:border-primary"
                >
                  <option value="">All States</option>
                  <option value="AL">Alabama</option>
                  <option value="AR">Arkansas</option>
                  <option value="TX">Texas</option>
                  <option value="FL">Florida</option>
                </select>
              </div>

              {/* County */}
              <div>
                <label className="block text-sm text-text-muted mb-1">County</label>
                <input
                  type="text"
                  value={county}
                  onChange={e => setCounty(e.target.value)}
                  placeholder="Any county"
                  className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary"
                />
              </div>

              {/* Min Score */}
              <div>
                <label className="block text-sm text-text-muted mb-1">Min Score</label>
                <input
                  type="number"
                  value={minScore}
                  onChange={e => setMinScore(e.target.value)}
                  placeholder="0"
                  min="0"
                  max="100"
                  className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary"
                />
              </div>

              {/* Min Price */}
              <div>
                <label className="block text-sm text-text-muted mb-1">Min Price</label>
                <input
                  type="number"
                  value={minPrice}
                  onChange={e => setMinPrice(e.target.value)}
                  placeholder="$0"
                  min="0"
                  className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary"
                />
              </div>

              {/* Max Price */}
              <div>
                <label className="block text-sm text-text-muted mb-1">Max Price</label>
                <input
                  type="number"
                  value={maxPrice}
                  onChange={e => setMaxPrice(e.target.value)}
                  placeholder="No limit"
                  min="0"
                  className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary"
                />
              </div>
            </div>

            {/* Checkboxes */}
            <div className="flex flex-wrap gap-4 mt-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={excludeRejects}
                  onChange={e => setExcludeRejects(e.target.checked)}
                  className="rounded border-neutral-1 text-primary focus:ring-primary"
                />
                <span className="text-sm text-text-primary">Exclude market rejects</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={excludeDelta}
                  onChange={e => setExcludeDelta(e.target.checked)}
                  className="rounded border-neutral-1 text-primary focus:ring-primary"
                />
                <span className="text-sm text-text-primary">Exclude Delta region</span>
              </label>
            </div>

            {/* Preview Button */}
            <div className="mt-4">
              <button
                onClick={fetchPreview}
                disabled={isLoadingPreview}
                className="flex items-center gap-2 px-4 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary hover:bg-neutral-1"
              >
                {isLoadingPreview ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
                Preview Export
              </button>
            </div>
          </div>

          {/* Column Selection */}
          <div className="bg-card rounded-lg p-6 border border-neutral-1">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-text-primary">Columns to Export</h2>
              <div className="flex gap-2">
                <button
                  onClick={selectDefaultColumns}
                  className="text-xs px-2 py-1 text-text-muted hover:text-primary"
                >
                  Default
                </button>
                <button
                  onClick={selectAllColumns}
                  className="text-xs px-2 py-1 text-text-muted hover:text-primary"
                >
                  Select All
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {AVAILABLE_COLUMNS.map(col => (
                <label key={col.key} className="flex items-center gap-2 cursor-pointer p-2 rounded hover:bg-surface">
                  <input
                    type="checkbox"
                    checked={selectedColumns.includes(col.key)}
                    onChange={() => toggleColumn(col.key)}
                    className="rounded border-neutral-1 text-primary focus:ring-primary"
                  />
                  <span className="text-sm text-text-primary">{col.label}</span>
                </label>
              ))}
            </div>

            <p className="text-xs text-text-muted mt-3">
              {selectedColumns.length} columns selected
            </p>
          </div>
        </div>

        {/* Export Actions */}
        <div className="space-y-6">
          {/* Preview Results */}
          {preview && (
            <div className="bg-card rounded-lg p-6 border border-neutral-1">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Preview</h2>

              <div className="text-center mb-4">
                <p className="text-3xl font-bold text-primary">{preview.total_matching.toLocaleString()}</p>
                <p className="text-sm text-text-muted">properties matching</p>
              </div>

              {preview.sample.length > 0 && (
                <div className="text-xs text-text-muted">
                  <p className="font-medium mb-1">Sample records:</p>
                  {preview.sample.slice(0, 3).map((p, i) => (
                    <p key={i} className="truncate">
                      {p.parcel_id} - ${p.amount?.toLocaleString()}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Export Buttons */}
          <div className="bg-card rounded-lg p-6 border border-neutral-1">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Export Format</h2>

            <div className="space-y-3">
              <button
                onClick={() => exportData('csv')}
                disabled={isExporting}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
              >
                {isExporting ? (
                  <RefreshCw className="w-5 h-5 animate-spin" />
                ) : (
                  <FileSpreadsheet className="w-5 h-5" />
                )}
                Export CSV
              </button>

              <button
                onClick={() => exportData('json')}
                disabled={isExporting}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-surface border border-neutral-1 text-text-primary rounded-lg hover:bg-neutral-1 disabled:opacity-50"
              >
                {isExporting ? (
                  <RefreshCw className="w-5 h-5 animate-spin" />
                ) : (
                  <FileJson className="w-5 h-5" />
                )}
                Export JSON
              </button>
            </div>

            <p className="text-xs text-text-muted mt-4">
              CSV is best for Excel/Sheets. JSON includes all metadata.
            </p>
          </div>

          {/* Export Limits */}
          <div className="bg-surface rounded-lg p-4 border border-neutral-1">
            <h3 className="text-sm font-medium text-text-primary mb-2">Export Limits</h3>
            <ul className="text-xs text-text-muted space-y-1">
              <li>Maximum 10,000 properties per export</li>
              <li>Use filters to narrow results</li>
              <li>Large exports may take a few seconds</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
