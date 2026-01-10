import React from 'react'
import { Property } from '../types'
import { FirstDealStage } from '../lib/api'
import {
  Search,
  Gavel,
  Trophy,
  FileText,
  CheckCircle2,
  ChevronRight,
  MapPin,
  X,
} from 'lucide-react'

interface PipelineStage {
  id: FirstDealStage
  label: string
  shortLabel: string
  icon: React.FC<{ className?: string }>
  stepIds: string[] // Maps to step IDs in MyFirstDeal
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: 'research',
    label: 'Research',
    shortLabel: 'Research',
    icon: Search,
    stepIds: ['research', 'due-diligence'],
  },
  {
    id: 'bid',
    label: 'Bidding',
    shortLabel: 'Bid',
    icon: Gavel,
    stepIds: ['bidding'],
  },
  {
    id: 'won',
    label: 'Won & Waiting',
    shortLabel: 'Won',
    icon: Trophy,
    stepIds: ['winning', 'redemption'],
  },
  {
    id: 'quiet_title',
    label: 'Quiet Title',
    shortLabel: 'Title',
    icon: FileText,
    stepIds: ['quiet-title'],
  },
  {
    id: 'sold',
    label: 'Complete',
    shortLabel: 'Done',
    icon: CheckCircle2,
    stepIds: ['sell-or-hold'],
  },
]

interface DealPipelineVisualProps {
  property: Property | null
  currentStage: FirstDealStage | null
  onStageClick?: (stage: FirstDealStage) => void
  onRemove?: () => void
  isRemoving?: boolean
  className?: string
}

/**
 * Visual pipeline component showing deal progress through stages.
 * Displays the assigned property and current stage with clickable navigation.
 */
export function DealPipelineVisual({
  property,
  currentStage,
  onStageClick,
  onRemove,
  isRemoving,
  className = '',
}: DealPipelineVisualProps) {
  // Find the index of the current stage
  const currentStageIndex = currentStage
    ? PIPELINE_STAGES.findIndex(s => s.id === currentStage)
    : -1

  // If no property assigned, show placeholder
  if (!property) {
    return (
      <div className={`bg-card rounded-lg border border-neutral-1 p-4 ${className}`}>
        <div className="text-center py-4">
          <p className="text-sm text-text-muted mb-2">No property assigned yet</p>
          <p className="text-xs text-text-muted">
            Click "Set as My First Deal" on a recommended property to start tracking
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-card rounded-lg border border-neutral-1 overflow-hidden ${className}`}>
      {/* Property Header */}
      <div className="p-4 border-b border-neutral-1 bg-surface">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-accent-primary uppercase tracking-wide">
                Your First Deal
              </span>
            </div>
            <p className="font-mono text-sm text-text-primary truncate mt-1">
              {property.parcel_id}
            </p>
            <p className="text-xs text-text-muted flex items-center gap-1 mt-0.5">
              <MapPin className="w-3 h-3" />
              {property.county}, {property.state}
            </p>
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-sm font-medium text-text-primary">
              ${property.effective_cost?.toLocaleString() || property.amount?.toLocaleString()}
            </p>
            <p className="text-xs text-text-muted">
              {property.acreage?.toFixed(2)} acres
            </p>
          </div>
          {onRemove && (
            <button
              onClick={onRemove}
              disabled={isRemoving}
              className="p-1 text-text-muted hover:text-danger transition-colors disabled:opacity-50"
              title="Remove from first deal tracking"
              aria-label="Remove first deal"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Pipeline Stages */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          {PIPELINE_STAGES.map((stage, index) => {
            const Icon = stage.icon
            const isCompleted = currentStageIndex > index
            const isCurrent = currentStageIndex === index
            const isPending = currentStageIndex < index

            return (
              <React.Fragment key={stage.id}>
                {/* Stage */}
                <button
                  onClick={() => onStageClick?.(stage.id)}
                  className={`
                    flex flex-col items-center gap-1.5 p-2 rounded-lg transition-all
                    ${isCurrent
                      ? 'bg-accent-primary/10 ring-2 ring-accent-primary'
                      : isCompleted
                        ? 'bg-success/10 hover:bg-success/20'
                        : 'hover:bg-surface'
                    }
                  `}
                  title={stage.label}
                >
                  <div
                    className={`
                      w-8 h-8 rounded-full flex items-center justify-center transition-colors
                      ${isCurrent
                        ? 'bg-accent-primary text-white'
                        : isCompleted
                          ? 'bg-success text-white'
                          : 'bg-surface text-text-muted'
                      }
                    `}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <span
                    className={`
                      text-xs font-medium
                      ${isCurrent
                        ? 'text-accent-primary'
                        : isCompleted
                          ? 'text-success'
                          : 'text-text-muted'
                      }
                    `}
                  >
                    {stage.shortLabel}
                  </span>
                </button>

                {/* Connector Line */}
                {index < PIPELINE_STAGES.length - 1 && (
                  <div className="flex-1 mx-1">
                    <div
                      className={`
                        h-0.5 rounded-full transition-colors
                        ${currentStageIndex > index
                          ? 'bg-success'
                          : 'bg-neutral-1'
                        }
                      `}
                    />
                  </div>
                )}
              </React.Fragment>
            )
          })}
        </div>

        {/* Current Stage Description */}
        {currentStage && (
          <div className="mt-4 pt-3 border-t border-neutral-1">
            <p className="text-xs text-text-muted text-center">
              {currentStage === 'research' && 'Researching and evaluating the property'}
              {currentStage === 'bid' && 'Preparing to bid or actively bidding'}
              {currentStage === 'won' && 'Waiting for redemption period to expire'}
              {currentStage === 'quiet_title' && 'Working with attorney on quiet title'}
              {currentStage === 'sold' && 'Deal complete - sold or holding'}
              {currentStage === 'holding' && 'Holding for appreciation'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Get the step IDs associated with a pipeline stage
 */
export function getStepIdsForStage(stage: FirstDealStage): string[] {
  const pipelineStage = PIPELINE_STAGES.find(s => s.id === stage)
  return pipelineStage?.stepIds || []
}

/**
 * Get the pipeline stage for a given step ID
 */
export function getStageForStepId(stepId: string): FirstDealStage | null {
  for (const stage of PIPELINE_STAGES) {
    if (stage.stepIds.includes(stepId)) {
      return stage.id
    }
  }
  return null
}

export default DealPipelineVisual
