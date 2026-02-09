import React, { useState, useEffect } from 'react'
import { DollarSign, MapPin, AlertTriangle, Check, RefreshCw, Info } from 'lucide-react'

// Types for settings API
interface UserPreferences {
  id: string
  investment_budget: number | null
  excluded_states: string[]
  preferred_states: string[]
  default_filters: Record<string, unknown>
  max_property_price: number | null
  notifications_enabled: boolean
  created_at: string | null
  updated_at: string | null
}

interface StateRecommendation {
  state_code: string
  state_name: string
  sale_type: string
  recommended: boolean
  reason: string
  time_to_ownership_days: number
  quiet_title_cost: number
  min_budget_recommended: number
}

interface BudgetRecommendations {
  budget: number
  recommendations: StateRecommendation[]
  summary: string
}

// Budget preset buttons
const BUDGET_PRESETS = [5000, 8000, 10000, 25000, 50000]

export function Settings() {
  const [, setPreferences] = useState<UserPreferences | null>(null)
  const [recommendations, setRecommendations] = useState<BudgetRecommendations | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Form state
  const [budget, setBudget] = useState<number>(10000)
  const [customBudget, setCustomBudget] = useState<string>('')
  const [maxPropertyPrice, setMaxPropertyPrice] = useState<number | null>(null)
  const [excludedStates, setExcludedStates] = useState<string[]>([])

  // Fetch settings on mount
  useEffect(() => {
    fetchSettings()
  }, [])

  // Fetch recommendations when budget changes
  useEffect(() => {
    if (budget > 0) {
      fetchRecommendations(budget)
    }
  }, [budget])

  const fetchSettings = async () => {
    try {
      setIsLoading(true)
      const response = await fetch('/api/v1/settings', {
        headers: {
          'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
        }
      })

      if (!response.ok) throw new Error('Failed to load settings')

      const data: UserPreferences = await response.json()
      setPreferences(data)
      setBudget(data.investment_budget || 10000)
      setMaxPropertyPrice(data.max_property_price)
      setExcludedStates(data.excluded_states || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchRecommendations = async (budgetAmount: number) => {
    try {
      const response = await fetch(`/api/v1/settings/budget-recommendations?budget=${budgetAmount}`, {
        headers: {
          'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
        }
      })

      if (!response.ok) throw new Error('Failed to load recommendations')

      const data: BudgetRecommendations = await response.json()
      setRecommendations(data)
    } catch (err) {
      console.error('Failed to load recommendations:', err)
    }
  }

  const saveSettings = async () => {
    try {
      setIsSaving(true)
      setError(null)
      setSuccessMessage(null)

      const response = await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
        },
        body: JSON.stringify({
          investment_budget: budget,
          max_property_price: maxPropertyPrice,
          excluded_states: excludedStates
        })
      })

      if (!response.ok) throw new Error('Failed to save settings')

      const data: UserPreferences = await response.json()
      setPreferences(data)
      setSuccessMessage('Settings saved successfully')

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setIsSaving(false)
    }
  }

  const handleBudgetPreset = (amount: number) => {
    setBudget(amount)
    setCustomBudget('')
  }

  const handleCustomBudget = () => {
    const amount = parseFloat(customBudget)
    if (!isNaN(amount) && amount > 0) {
      setBudget(amount)
    }
  }

  const toggleExcludedState = (stateCode: string) => {
    setExcludedStates(prev =>
      prev.includes(stateCode)
        ? prev.filter(s => s !== stateCode)
        : [...prev, stateCode]
    )
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-text-primary mb-2">Settings</h1>
          <p className="text-text-muted">Application configuration and preferences</p>
        </div>
        <div className="animate-pulse space-y-6">
          <div className="bg-card rounded-lg p-6 border border-neutral-1 h-48"></div>
          <div className="bg-card rounded-lg p-6 border border-neutral-1 h-64"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Settings</h1>
        <p className="text-text-muted">Configure your investment preferences and filters</p>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="mb-6 p-4 bg-danger/10 border border-danger/20 rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-danger" />
          <p className="text-danger text-sm">{error}</p>
        </div>
      )}

      {successMessage && (
        <div className="mb-6 p-4 bg-success/10 border border-success/20 rounded-lg flex items-center gap-2">
          <Check className="w-5 h-5 text-success" />
          <p className="text-success text-sm">{successMessage}</p>
        </div>
      )}

      <div className="space-y-6">
        {/* Investment Budget Section */}
        <div className="bg-card rounded-lg p-6 border border-neutral-1">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-text-primary">Investment Budget</h2>
          </div>

          <p className="text-text-muted text-sm mb-4">
            Set your total investment capital. This affects which states are recommended based on
            redemption periods, quiet title costs, and capital requirements.
          </p>

          {/* Budget Presets */}
          <div className="flex flex-wrap gap-2 mb-4">
            {BUDGET_PRESETS.map(amount => (
              <button
                key={amount}
                onClick={() => handleBudgetPreset(amount)}
                className={`px-4 py-2 rounded-lg border transition-colors ${
                  budget === amount
                    ? 'bg-primary text-white border-primary'
                    : 'bg-surface border-neutral-1 text-text-primary hover:border-primary'
                }`}
              >
                ${amount.toLocaleString()}
              </button>
            ))}
          </div>

          {/* Custom Budget Input */}
          <div className="flex gap-2 mb-4">
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">$</span>
              <input
                type="number"
                value={customBudget}
                onChange={e => setCustomBudget(e.target.value)}
                placeholder="Custom amount"
                className="w-full pl-7 pr-4 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary"
              />
            </div>
            <button
              onClick={handleCustomBudget}
              disabled={!customBudget}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Set
            </button>
          </div>

          {/* Current Budget Display */}
          <div className="p-4 bg-surface rounded-lg">
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Current Budget:</span>
              <span className="text-2xl font-bold text-primary">${budget.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* State Recommendations Section */}
        <div className="bg-card rounded-lg p-6 border border-neutral-1">
          <div className="flex items-center gap-2 mb-4">
            <MapPin className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-text-primary">State Recommendations</h2>
          </div>

          {recommendations && (
            <>
              {/* Summary */}
              <div className="p-4 bg-primary/10 border border-primary/20 rounded-lg mb-4">
                <div className="flex items-start gap-2">
                  <Info className="w-5 h-5 text-primary mt-0.5" />
                  <p className="text-text-primary text-sm">{recommendations.summary}</p>
                </div>
              </div>

              {/* State Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {recommendations.recommendations.map(rec => (
                  <div
                    key={rec.state_code}
                    className={`p-4 rounded-lg border ${
                      rec.recommended
                        ? 'bg-success/5 border-success/20'
                        : 'bg-surface border-neutral-1'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-semibold text-text-primary">
                          {rec.state_name} ({rec.state_code})
                        </h3>
                        <p className="text-xs text-text-muted capitalize">
                          {rec.sale_type.replace('_', ' ')}
                        </p>
                      </div>
                      {rec.recommended ? (
                        <span className="px-2 py-1 bg-success/20 text-success text-xs rounded-full">
                          Recommended
                        </span>
                      ) : (
                        <button
                          onClick={() => toggleExcludedState(rec.state_code)}
                          className={`px-2 py-1 text-xs rounded-full ${
                            excludedStates.includes(rec.state_code)
                              ? 'bg-danger/20 text-danger'
                              : 'bg-neutral-1 text-text-muted'
                          }`}
                        >
                          {excludedStates.includes(rec.state_code) ? 'Excluded' : 'Not Recommended'}
                        </button>
                      )}
                    </div>

                    <p className="text-sm text-text-muted mb-3">{rec.reason}</p>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-text-muted">Time to Own:</span>
                        <span className="ml-1 text-text-primary">{rec.time_to_ownership_days} days</span>
                      </div>
                      <div>
                        <span className="text-text-muted">Quiet Title:</span>
                        <span className="ml-1 text-text-primary">${rec.quiet_title_cost.toLocaleString()}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-text-muted">Min Budget:</span>
                        <span className="ml-1 text-text-primary">${rec.min_budget_recommended.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Max Property Price Section */}
        <div className="bg-card rounded-lg p-6 border border-neutral-1">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Price Limits</h2>

          <p className="text-text-muted text-sm mb-4">
            Set a maximum price per property. Defaults to 50% of your budget to leave room for
            quiet title costs and other fees.
          </p>

          <div className="flex gap-2 items-center">
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">$</span>
              <input
                type="number"
                value={maxPropertyPrice || ''}
                onChange={e => setMaxPropertyPrice(e.target.value ? parseFloat(e.target.value) : null)}
                placeholder={`Default: $${Math.round(budget * 0.5).toLocaleString()}`}
                className="w-full pl-7 pr-4 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary"
              />
            </div>
            <button
              onClick={() => setMaxPropertyPrice(null)}
              className="px-3 py-2 text-text-muted hover:text-text-primary"
              title="Reset to default"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end gap-4">
          <button
            onClick={fetchSettings}
            className="px-6 py-2 border border-neutral-1 text-text-primary rounded-lg hover:bg-surface"
          >
            Reset
          </button>
          <button
            onClick={saveSettings}
            disabled={isSaving}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
          >
            {isSaving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Save Settings
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
