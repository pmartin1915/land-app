import React from 'react'

export function Settings() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Settings</h1>
        <p className="text-text-muted">Application configuration and preferences</p>
      </div>

      <div className="space-y-6">
        <div className="bg-card rounded-lg p-6 border border-neutral-1">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Theme</h2>
          <p className="text-text-muted">Theme management coming soon...</p>
        </div>

        <div className="bg-card rounded-lg p-6 border border-neutral-1">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Counties & Mapping</h2>
          <p className="text-text-muted">County configuration coming soon...</p>
        </div>

        <div className="bg-card rounded-lg p-6 border border-neutral-1">
          <h2 className="text-lg font-semibold text-text-primary mb-4">AI Rules</h2>
          <p className="text-text-muted">AI rule management coming soon...</p>
        </div>
      </div>
    </div>
  )
}