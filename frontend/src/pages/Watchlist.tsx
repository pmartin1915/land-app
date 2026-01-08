import React, { useState, useEffect } from 'react'
import { Star, Trash2, StickyNote, AlertTriangle, RefreshCw, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import { api } from '../lib/api'

// Types
interface PropertyInteraction {
  id: string
  device_id: string
  property_id: string
  is_watched: boolean
  star_rating: number | null
  user_notes: string | null
  dismissed: boolean
  created_at: string | null
  updated_at: string | null
}

interface Property {
  id: string
  parcel_id: string
  state: string
  county: string
  amount: number
  acreage: number | null
  price_per_acre: number | null
  investment_score: number | null
  buy_hold_score: number | null
  wholesale_score: number | null
  water_score: number
  description: string | null
  status: string
  created_at: string | null
}

interface WatchlistItem {
  interaction: PropertyInteraction
  property: Property
}

interface WatchlistResponse {
  items: WatchlistItem[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
}

interface WatchlistStats {
  watched: number
  rated: number
  dismissed: number
  with_notes: number
  total_interactions: number
}

export function Watchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistResponse | null>(null)
  const [stats, setStats] = useState<WatchlistStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [editingNotes, setEditingNotes] = useState<string | null>(null)
  const [noteText, setNoteText] = useState('')
  const [updatingRatings, setUpdatingRatings] = useState<Set<string>>(new Set())
  const [savingNotesSet, setSavingNotesSet] = useState<Set<string>>(new Set())

  const pageSize = 20

  useEffect(() => {
    fetchWatchlist()
    fetchStats()
  }, [page])

  const fetchWatchlist = async () => {
    try {
      setIsLoading(true)
      const data: WatchlistResponse = await api.watchlist.getWatchlist(page, pageSize)
      setWatchlist(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load watchlist')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const data: WatchlistStats = await api.watchlist.getStats()
      setStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }

  const removeFromWatchlist = async (propertyId: string) => {
    try {
      await api.watchlist.toggleWatch(propertyId)
      // Refresh list
      fetchWatchlist()
      fetchStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update watchlist')
    }
  }

  const updateRating = async (propertyId: string, rating: number) => {
    // Check if THIS property is already updating (allows concurrent updates on different properties)
    if (updatingRatings.has(propertyId)) return

    // Capture previous state for rollback
    const previousWatchlist = watchlist

    try {
      // Add to in-flight set
      setUpdatingRatings(prev => new Set(prev).add(propertyId))

      // Optimistic update
      setWatchlist(prev => {
        if (!prev) return prev
        return {
          ...prev,
          items: prev.items.map(item =>
            item.property.id === propertyId
              ? { ...item, interaction: { ...item.interaction, star_rating: rating } }
              : item
          )
        }
      })

      await api.watchlist.updateInteraction(propertyId, { star_rating: rating })
    } catch (err) {
      // Rollback on error
      setWatchlist(previousWatchlist)
      setError(err instanceof Error ? err.message : 'Failed to update rating')
    } finally {
      // Remove from in-flight set
      setUpdatingRatings(prev => {
        const next = new Set(prev)
        next.delete(propertyId)
        return next
      })
    }
  }

  const saveNotes = async (propertyId: string) => {
    // Check if THIS property is already saving (allows concurrent saves on different properties)
    if (savingNotesSet.has(propertyId)) return

    // Capture previous state for rollback
    const previousWatchlist = watchlist
    const savedNoteText = noteText

    try {
      // Add to in-flight set
      setSavingNotesSet(prev => new Set(prev).add(propertyId))

      // Optimistic update
      setWatchlist(prev => {
        if (!prev) return prev
        return {
          ...prev,
          items: prev.items.map(item =>
            item.property.id === propertyId
              ? { ...item, interaction: { ...item.interaction, user_notes: savedNoteText } }
              : item
          )
        }
      })

      await api.watchlist.updateInteraction(propertyId, { user_notes: savedNoteText })

      setEditingNotes(null)
      setNoteText('')
    } catch (err) {
      // Rollback on error
      setWatchlist(previousWatchlist)
      setError(err instanceof Error ? err.message : 'Failed to save notes')
    } finally {
      // Remove from in-flight set
      setSavingNotesSet(prev => {
        const next = new Set(prev)
        next.delete(propertyId)
        return next
      })
    }
  }

  const startEditingNotes = (propertyId: string, currentNotes: string | null) => {
    setEditingNotes(propertyId)
    setNoteText(currentNotes || '')
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
  }

  const formatScore = (score: number | null) => {
    if (score === null) return '-'
    return score.toFixed(0)
  }

  if (isLoading && !watchlist) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-text-primary mb-2">Watchlist</h1>
          <p className="text-text-muted">Tracked properties with notes and ratings</p>
        </div>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-card rounded-lg p-6 border border-neutral-1 h-32"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Watchlist</h1>
        <p className="text-text-muted">Tracked properties with notes and ratings</p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-danger/10 border border-danger/20 rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-danger" />
          <p className="text-danger text-sm">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto text-danger hover:text-danger/80">
            Dismiss
          </button>
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-card rounded-lg p-4 border border-neutral-1">
            <div className="text-2xl font-bold text-primary">{stats.watched}</div>
            <div className="text-sm text-text-muted">Watched</div>
          </div>
          <div className="bg-card rounded-lg p-4 border border-neutral-1">
            <div className="text-2xl font-bold text-warning">{stats.rated}</div>
            <div className="text-sm text-text-muted">Rated</div>
          </div>
          <div className="bg-card rounded-lg p-4 border border-neutral-1">
            <div className="text-2xl font-bold text-success">{stats.with_notes}</div>
            <div className="text-sm text-text-muted">With Notes</div>
          </div>
          <div className="bg-card rounded-lg p-4 border border-neutral-1">
            <div className="text-2xl font-bold text-text-muted">{stats.dismissed}</div>
            <div className="text-sm text-text-muted">Dismissed</div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {watchlist && watchlist.items.length === 0 && (
        <div className="bg-card rounded-lg p-12 border border-neutral-1 text-center">
          <Star className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">No watched properties</h3>
          <p className="text-text-muted">
            Star properties from the Parcels page to add them to your watchlist.
          </p>
        </div>
      )}

      {/* Watchlist Items */}
      {watchlist && watchlist.items.length > 0 && (
        <div className="space-y-4">
          {watchlist.items.map(({ interaction, property }) => (
            <div key={property.id} className="bg-card rounded-lg border border-neutral-1 overflow-hidden">
              <div className="p-4">
                {/* Header Row */}
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-semibold text-text-primary">{property.parcel_id}</h3>
                    <p className="text-sm text-text-muted">
                      {property.county}, {property.state}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* Star Rating */}
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map(rating => (
                        <button
                          key={rating}
                          onClick={() => updateRating(property.id, rating)}
                          disabled={updatingRatings.has(property.id)}
                          aria-label={`Rate ${rating} star${rating > 1 ? 's' : ''}${interaction.star_rating === rating ? ' (current rating)' : ''}`}
                          className={`p-0.5 ${updatingRatings.has(property.id) ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                          <Star
                            className={`w-5 h-5 ${
                              interaction.star_rating && rating <= interaction.star_rating
                                ? 'text-warning fill-warning'
                                : 'text-neutral-1'
                            }`}
                          />
                        </button>
                      ))}
                    </div>
                    {/* Remove Button */}
                    <button
                      onClick={() => removeFromWatchlist(property.id)}
                      className="p-2 text-text-muted hover:text-danger"
                      title="Remove from watchlist"
                      aria-label="Remove from watchlist"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Property Details */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                  <div>
                    <span className="text-xs text-text-muted">Price</span>
                    <p className="font-semibold text-text-primary">{formatCurrency(property.amount)}</p>
                  </div>
                  <div>
                    <span className="text-xs text-text-muted">Acreage</span>
                    <p className="font-semibold text-text-primary">
                      {property.acreage ? `${property.acreage.toFixed(2)} ac` : '-'}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-text-muted">Investment Score</span>
                    <p className="font-semibold text-text-primary">{formatScore(property.investment_score)}</p>
                  </div>
                  <div>
                    <span className="text-xs text-text-muted">Status</span>
                    <p className={`font-semibold capitalize ${
                      property.status === 'bid_ready' ? 'text-success' :
                      property.status === 'rejected' ? 'text-danger' :
                      'text-text-primary'
                    }`}>
                      {property.status.replace('_', ' ')}
                    </p>
                  </div>
                </div>

                {/* Description */}
                {property.description && (
                  <p className="text-sm text-text-muted mb-3 line-clamp-2">
                    {property.description}
                  </p>
                )}

                {/* Notes Section */}
                <div className="border-t border-neutral-1 pt-3">
                  {editingNotes === property.id ? (
                    <div className="space-y-2">
                      <textarea
                        value={noteText}
                        onChange={e => setNoteText(e.target.value)}
                        placeholder="Add notes about this property..."
                        className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary resize-none"
                        rows={3}
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => saveNotes(property.id)}
                          disabled={savingNotesSet.has(property.id)}
                          className="px-3 py-1 bg-primary text-white text-sm rounded hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {savingNotesSet.has(property.id) ? 'Saving...' : 'Save'}
                        </button>
                        <button
                          onClick={() => {
                            setEditingNotes(null)
                            setNoteText('')
                          }}
                          disabled={savingNotesSet.has(property.id)}
                          className="px-3 py-1 border border-neutral-1 text-text-primary text-sm rounded hover:bg-surface disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start gap-2">
                      <StickyNote className="w-4 h-4 text-text-muted mt-0.5" />
                      {interaction.user_notes ? (
                        <p
                          className="text-sm text-text-primary flex-1 cursor-pointer hover:text-primary"
                          onClick={() => startEditingNotes(property.id, interaction.user_notes)}
                        >
                          {interaction.user_notes}
                        </p>
                      ) : (
                        <button
                          onClick={() => startEditingNotes(property.id, null)}
                          className="text-sm text-text-muted hover:text-primary"
                        >
                          Add notes...
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {watchlist && watchlist.total_pages > 1 && (
        <div className="flex justify-center items-center gap-4 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 border border-neutral-1 rounded-lg disabled:opacity-50"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="text-text-muted">
            Page {watchlist.page} of {watchlist.total_pages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(watchlist.total_pages, p + 1))}
            disabled={page === watchlist.total_pages}
            className="p-2 border border-neutral-1 rounded-lg disabled:opacity-50"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Refresh Button */}
      <div className="flex justify-center mt-6">
        <button
          onClick={() => {
            fetchWatchlist()
            fetchStats()
          }}
          className="flex items-center gap-2 px-4 py-2 text-text-muted hover:text-text-primary"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>
    </div>
  )
}
