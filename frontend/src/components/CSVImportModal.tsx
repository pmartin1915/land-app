import React, { useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Upload, FileSpreadsheet, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { importApi, CSVPreviewResponse, CSVImportResult } from '../lib/api'
import { useFocusTrap } from '../lib/useFocusTrap'

interface CSVImportModalProps {
  isOpen: boolean
  onClose: () => void
  onImportComplete?: (result: CSVImportResult) => void
}

type ImportStep = 'upload' | 'preview' | 'importing' | 'complete'

const FIELD_LABELS: Record<string, string> = {
  parcel_id: 'Parcel ID',
  amount: 'Amount',
  acreage: 'Acreage',
  county: 'County',
  state: 'State',
  description: 'Description',
  owner_name: 'Owner Name',
  year_sold: 'Year Sold',
  assessed_value: 'Assessed Value',
  sale_type: 'Sale Type',
  redemption_period_days: 'Redemption Days',
  auction_date: 'Auction Date',
  auction_platform: 'Auction Platform',
  data_source: 'Data Source',
  estimated_market_value: 'Market Value',
}

export function CSVImportModal({ isOpen, onClose, onImportComplete }: CSVImportModalProps) {
  const [step, setStep] = useState<ImportStep>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<CSVPreviewResponse | null>(null)
  const [mapping, setMapping] = useState<Record<string, string | null>>({})
  const [skipDuplicates, setSkipDuplicates] = useState(true)
  const [defaultState, setDefaultState] = useState('AL')
  const [result, setResult] = useState<CSVImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const focusTrapRef = useFocusTrap<HTMLDivElement>(isOpen)

  const resetModal = useCallback(() => {
    setStep('upload')
    setFile(null)
    setPreview(null)
    setMapping({})
    setResult(null)
    setError(null)
    setIsLoading(false)
  }, [])

  const handleClose = useCallback(() => {
    resetModal()
    onClose()
  }, [onClose, resetModal])

  const handleFileSelect = useCallback(async (selectedFile: File) => {
    setFile(selectedFile)
    setError(null)
    setIsLoading(true)

    try {
      const previewData = await importApi.previewCSV(selectedFile)
      setPreview(previewData)
      setMapping(previewData.suggested_mapping)
      setStep('preview')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to preview CSV file')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.name.toLowerCase().endsWith('.csv')) {
      handleFileSelect(droppedFile)
    } else {
      setError('Please drop a CSV file')
    }
  }, [handleFileSelect])

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      handleFileSelect(selectedFile)
    }
  }, [handleFileSelect])

  const handleMappingChange = useCallback((field: string, column: string | null) => {
    setMapping(prev => ({ ...prev, [field]: column }))
  }, [])

  const handleImport = useCallback(async () => {
    if (!file) return

    setStep('importing')
    setError(null)

    try {
      // Convert mapping to the format expected by the API
      const mappingForApi: Record<string, string> = {}
      for (const [field, col] of Object.entries(mapping)) {
        if (col) {
          mappingForApi[field] = col
        }
      }

      const importResult = await importApi.importCSV(file, {
        skipDuplicates,
        defaultState,
        mapping: mappingForApi,
      })

      setResult(importResult)
      setStep('complete')
      onImportComplete?.(importResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
      setStep('preview')
    }
  }, [file, mapping, skipDuplicates, defaultState, onImportComplete])

  const canImport = mapping.parcel_id && mapping.amount

  if (!isOpen) return null

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 bg-black/50 z-50"
          />

          {/* Modal */}
          <motion.div
            ref={focusTrapRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="csv-import-modal-title"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-4 md:inset-10 lg:inset-20 bg-bg rounded-lg shadow-elevated z-50 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-neutral-1 bg-surface">
              <div>
                <h2 id="csv-import-modal-title" className="text-lg font-semibold text-text-primary">Import CSV</h2>
                <p className="text-sm text-text-muted">
                  {step === 'upload' && 'Upload a CSV file with property data'}
                  {step === 'preview' && 'Review and map columns'}
                  {step === 'importing' && 'Importing properties...'}
                  {step === 'complete' && 'Import complete'}
                </p>
              </div>
              <button
                onClick={handleClose}
                className="p-2 hover:bg-card rounded transition-colors"
                aria-label="Close import modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
              {/* Upload Step */}
              {step === 'upload' && (
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  className="h-full flex flex-col items-center justify-center border-2 border-dashed border-neutral-1 rounded-lg p-8 hover:border-accent-primary transition-colors cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    onChange={handleFileInputChange}
                    className="hidden"
                  />
                  {isLoading ? (
                    <Loader2 className="w-12 h-12 text-accent-primary animate-spin" />
                  ) : (
                    <>
                      <FileSpreadsheet className="w-12 h-12 text-text-muted mb-4" />
                      <p className="text-lg font-medium text-text-primary mb-2">
                        Drop your CSV file here
                      </p>
                      <p className="text-sm text-text-muted mb-4">
                        or click to browse
                      </p>
                      <button className="px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-opacity-90 transition-colors flex items-center gap-2">
                        <Upload className="w-4 h-4" />
                        Select File
                      </button>
                    </>
                  )}
                </div>
              )}

              {/* Preview Step */}
              {step === 'preview' && preview && (
                <div className="space-y-6">
                  {/* File Info */}
                  <div className="flex items-center gap-3 p-3 bg-surface rounded-lg">
                    <FileSpreadsheet className="w-6 h-6 text-accent-primary" />
                    <div>
                      <p className="font-medium text-text-primary">{file?.name}</p>
                      <p className="text-sm text-text-muted">
                        {preview.total_rows} rows, {preview.headers.length} columns
                        {preview.potential_duplicates > 0 && (
                          <span className="text-warning ml-2">
                            ({preview.potential_duplicates} potential duplicates)
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  {/* Column Mapping */}
                  <div>
                    <h3 className="font-medium text-text-primary mb-3">Column Mapping</h3>
                    <p className="text-sm text-text-muted mb-4">
                      Map your CSV columns to property fields. Parcel ID and Amount are required.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {Object.entries(FIELD_LABELS).map(([field, label]) => (
                        <div key={field} className="flex items-center gap-2">
                          <label className="text-sm text-text-muted w-28 flex-shrink-0">
                            {label}
                            {(field === 'parcel_id' || field === 'amount') && (
                              <span className="text-danger ml-1">*</span>
                            )}
                          </label>
                          <select
                            value={mapping[field] || ''}
                            onChange={(e) => handleMappingChange(field, e.target.value || null)}
                            className="flex-1 px-2 py-1 bg-surface border border-neutral-1 rounded text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
                          >
                            <option value="">-- Not mapped --</option>
                            {preview.headers.map((header) => (
                              <option key={header} value={header}>
                                {header}
                              </option>
                            ))}
                          </select>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Import Options */}
                  <div className="flex flex-wrap gap-4 p-3 bg-surface rounded-lg">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={skipDuplicates}
                        onChange={(e) => setSkipDuplicates(e.target.checked)}
                        className="rounded border-neutral-1 text-accent-primary focus:ring-accent-primary"
                      />
                      <span className="text-sm text-text-primary">Skip duplicate parcel IDs</span>
                    </label>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-text-muted">Default state:</span>
                      <select
                        value={defaultState}
                        onChange={(e) => setDefaultState(e.target.value)}
                        className="px-2 py-1 bg-bg border border-neutral-1 rounded text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
                      >
                        <option value="AL">Alabama</option>
                        <option value="AR">Arkansas</option>
                        <option value="TX">Texas</option>
                        <option value="FL">Florida</option>
                      </select>
                    </div>
                  </div>

                  {/* Data Preview */}
                  <div>
                    <h3 className="font-medium text-text-primary mb-3">Data Preview</h3>
                    <div className="overflow-x-auto border border-neutral-1 rounded-lg">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-surface">
                            {preview.headers.map((header) => (
                              <th key={header} className="px-3 py-2 text-left text-text-muted font-medium whitespace-nowrap">
                                {header}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {preview.rows.slice(0, 5).map((row, rowIdx) => (
                            <tr key={rowIdx} className="border-t border-neutral-1">
                              {row.map((cell, cellIdx) => (
                                <td key={cellIdx} className="px-3 py-2 text-text-primary whitespace-nowrap">
                                  {cell || <span className="text-text-muted">--</span>}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {preview.total_rows > 5 && (
                      <p className="text-sm text-text-muted mt-2">
                        Showing first 5 of {preview.total_rows} rows
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Importing Step */}
              {step === 'importing' && (
                <div className="h-full flex flex-col items-center justify-center">
                  <Loader2 className="w-12 h-12 text-accent-primary animate-spin mb-4" />
                  <p className="text-lg font-medium text-text-primary">Importing properties...</p>
                  <p className="text-sm text-text-muted">This may take a moment</p>
                </div>
              )}

              {/* Complete Step */}
              {step === 'complete' && result && (
                <div className="h-full flex flex-col items-center justify-center">
                  <CheckCircle className="w-12 h-12 text-success mb-4" />
                  <p className="text-lg font-medium text-text-primary mb-6">Import Complete</p>

                  <div className="grid grid-cols-3 gap-6 text-center mb-6">
                    <div>
                      <p className="text-3xl font-bold text-success">{result.imported}</p>
                      <p className="text-sm text-text-muted">Imported</p>
                    </div>
                    <div>
                      <p className="text-3xl font-bold text-warning">{result.skipped_duplicates}</p>
                      <p className="text-sm text-text-muted">Duplicates Skipped</p>
                    </div>
                    <div>
                      <p className="text-3xl font-bold text-danger">{result.errors}</p>
                      <p className="text-sm text-text-muted">Errors</p>
                    </div>
                  </div>

                  {result.failed_rows.length > 0 && (
                    <div className="w-full max-w-lg">
                      <h3 className="font-medium text-text-primary mb-2">Errors:</h3>
                      <div className="max-h-40 overflow-y-auto bg-surface rounded-lg p-3 text-sm">
                        {result.failed_rows.slice(0, 10).map((err, idx) => (
                          <div key={idx} className="flex gap-2 text-danger">
                            <span className="text-text-muted">Row {err.row}:</span>
                            <span>{err.error}</span>
                          </div>
                        ))}
                        {result.failed_rows.length > 10 && (
                          <p className="text-text-muted mt-2">
                            +{result.failed_rows.length - 10} more errors
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="flex items-center gap-2 p-3 bg-danger/10 text-danger rounded-lg mt-4">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <p className="text-sm">{error}</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between p-4 border-t border-neutral-1 bg-surface">
              <button
                onClick={step === 'complete' ? resetModal : handleClose}
                className="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors"
              >
                {step === 'complete' ? 'Import Another' : 'Cancel'}
              </button>

              <div className="flex gap-2">
                {step === 'preview' && (
                  <>
                    <button
                      onClick={() => {
                        setStep('upload')
                        setFile(null)
                        setPreview(null)
                      }}
                      className="px-4 py-2 text-sm text-text-primary hover:bg-card rounded-lg transition-colors"
                    >
                      Back
                    </button>
                    <button
                      onClick={handleImport}
                      disabled={!canImport}
                      className="px-4 py-2 bg-accent-primary text-white text-sm rounded-lg hover:bg-opacity-90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      <Upload className="w-4 h-4" />
                      Import {preview?.total_rows} Properties
                    </button>
                  </>
                )}
                {step === 'complete' && (
                  <button
                    onClick={handleClose}
                    className="px-4 py-2 bg-accent-primary text-white text-sm rounded-lg hover:bg-opacity-90 transition-colors"
                  >
                    Done
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export default CSVImportModal
