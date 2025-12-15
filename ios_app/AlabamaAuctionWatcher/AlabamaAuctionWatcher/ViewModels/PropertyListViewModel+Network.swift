//
//  PropertyListViewModel+Network.swift
//  AlabamaAuctionWatcher
//
//  Network integration for PropertyListViewModel
//  Provides sync capabilities while maintaining offline-first approach
//

import Foundation
import CoreData
import Combine

// MARK: - Network-Enhanced PropertyListViewModel

extension PropertyListViewModel {

    // MARK: - Published Network Properties

    @Published var isSyncing = false
    @Published var lastSyncDate: Date?
    @Published var syncStatus: SyncStatus = .idle
    @Published var networkError: NetworkError?
    @Published var hasNetworkConnection = true

    enum SyncStatus {
        case idle
        case syncing
        case success
        case failed(String)
        case conflictsDetected(Int)
    }

    // MARK: - Network Integration Setup

    func setupNetworkIntegration() {
        // Load last sync date
        lastSyncDate = UserDefaults.standard.object(forKey: "lastSyncDate") as? Date

        // Monitor network connectivity
        NetworkManager.shared.$isConnected
            .assign(to: \.hasNetworkConnection, on: self)
            .store(in: &cancellables)

        // Monitor network loading state
        NetworkManager.shared.$isLoading
            .assign(to: \.isSyncing, on: self)
            .store(in: &cancellables)

        // Auto-sync when coming online
        NetworkManager.shared.$isConnected
            .removeDuplicates()
            .sink { [weak self] isConnected in
                if isConnected {
                    Task {
                        await self?.syncWithBackendIfNeeded()
                    }
                }
            }
            .store(in: &cancellables)
    }

    // MARK: - Network Operations

    /// Sync properties with backend (delta or full sync)
    func syncWithBackend() async {
        guard hasNetworkConnection else {
            syncStatus = .failed("No network connection")
            return
        }

        syncStatus = .syncing
        isSyncing = true

        do {
            // Ensure API key is configured
            if NetworkManager.shared.apiKeyStatus != "Configured" {
                try await NetworkManager.shared.createAPIKey()
            }

            // Perform delta sync if we have a last sync date, otherwise full sync
            if let lastSync = lastSyncDate {
                try await performDeltaSync(since: lastSync)
            } else {
                try await performFullSync()
            }

            lastSyncDate = Date()
            UserDefaults.standard.set(lastSyncDate, forKey: "lastSyncDate")
            syncStatus = .success

        } catch NetworkError.syncConflict(let conflicts) {
            syncStatus = .conflictsDetected(conflicts.count)
            // Handle conflicts - for now, use last-write-wins
            await handleSyncConflicts(conflicts)

        } catch NetworkError.algorithmMismatch(let message) {
            syncStatus = .failed("Algorithm compatibility issue: \(message)")
            networkError = NetworkError.algorithmMismatch(message)

        } catch {
            syncStatus = .failed(error.localizedDescription)
            networkError = error as? NetworkError
        }

        isSyncing = false
    }

    /// Perform delta sync with backend
    private func performDeltaSync(since lastSyncDate: Date) async throws {
        // Get local changes since last sync
        let context = persistenceController.container.viewContext
        let localChanges = try Property.fetchPropertiesForSync(since: lastSyncDate, context: context)

        // Convert to PropertyChange objects
        let changes = localChanges.map { property in
            property.createPropertyChange(
                operation: property.isDeleted ? "delete" : "update",
                deviceId: UIDevice.current.identifierForVendor?.uuidString ?? "unknown"
            )
        }

        // Perform delta sync
        let response = try await NetworkManager.shared.performDeltaSync(
            lastSyncTimestamp: lastSyncDate,
            changes: changes
        )

        // Apply server changes to Core Data
        try await applyServerChanges(response.serverChanges)

        print("✅ Delta sync completed: \(response.changesApplied) applied, \(response.serverChangesCount) from server")
    }

    /// Perform full sync with backend
    private func performFullSync() async throws {
        let apiProperties = try await NetworkManager.shared.performFullSync()

        // Update Core Data with all properties from API
        let context = persistenceController.container.newBackgroundContext()

        await context.perform {
            do {
                // Clear existing properties (or mark as needs update)
                let existingProperties = try Property.getAllCountries(context: context)
                for property in existingProperties {
                    // Mark as potentially outdated
                    property.needsUpdate = true
                }

                // Add/update properties from API
                for apiProperty in apiProperties {
                    if let existingProperty = Property.findProperty(by: apiProperty.parcelId, in: context) {
                        existingProperty.updateFromAPIModel(apiProperty, context: context)
                        existingProperty.needsUpdate = false
                    } else {
                        let newProperty = Property.createFromAPIModel(apiProperty, context: context)
                        newProperty.needsUpdate = false
                    }
                }

                try context.save()

                // Refresh main context
                DispatchQueue.main.async {
                    self.persistenceController.container.viewContext.refreshAllObjects()
                    self.loadProperties()
                }

            } catch {
                print("❌ Full sync failed: \(error)")
                throw error
            }
        }

        print("✅ Full sync completed: \(apiProperties.count) properties synced")
    }

    /// Apply server changes to Core Data
    private func applyServerChanges(_ serverChanges: [PropertyChange]) async throws {
        guard !serverChanges.isEmpty else { return }

        let context = persistenceController.container.newBackgroundContext()

        await context.perform {
            do {
                for change in serverChanges {
                    switch change.operation {
                    case "create", "update":
                        if let changeData = change.data {
                            // Convert PropertyChange data to APIProperty
                            let apiProperty = try self.convertPropertyChangeToAPIProperty(change)

                            if let existingProperty = Property.findProperty(by: apiProperty.parcelId, in: context) {
                                existingProperty.updateFromAPIModel(apiProperty, context: context)
                            } else {
                                _ = Property.createFromAPIModel(apiProperty, context: context)
                            }
                        }

                    case "delete":
                        if let existingProperty = Property.findProperty(by: change.propertyId, in: context) {
                            context.delete(existingProperty)
                        }

                    default:
                        print("⚠️ Unknown operation: \(change.operation)")
                    }
                }

                try context.save()

                // Refresh main context
                DispatchQueue.main.async {
                    self.persistenceController.container.viewContext.refreshAllObjects()
                    self.loadProperties()
                }

            } catch {
                print("❌ Failed to apply server changes: \(error)")
                throw error
            }
        }
    }

    /// Handle sync conflicts using last-write-wins strategy
    private func handleSyncConflicts(_ conflicts: [SyncConflict]) async {
        // For now, implement last-write-wins strategy
        // In the future, this could present a UI for user to choose resolution

        for conflict in conflicts {
            let localTime = Date.fromISO8601String(conflict.localTimestamp) ?? Date.distantPast
            let remoteTime = Date.fromISO8601String(conflict.remoteTimestamp) ?? Date.distantPast

            if remoteTime > localTime {
                // Remote wins - update local property
                if let apiProperty = try? convertSyncConflictToAPIProperty(conflict) {
                    let context = persistenceController.container.viewContext
                    if let localProperty = Property.findProperty(by: apiProperty.parcelId, in: context) {
                        localProperty.updateFromAPIModel(apiProperty, context: context)
                        try? context.save()
                    }
                }
            }
            // If local wins, no action needed as local data is already present
        }

        print("🔄 Resolved \(conflicts.count) sync conflicts using last-write-wins")
    }

    // MARK: - Data Conversion Helpers

    private func convertPropertyChangeToAPIProperty(_ change: PropertyChange) throws -> APIProperty {
        guard let data = change.data else {
            throw NetworkError.decodingError("Missing property data in change")
        }

        return APIProperty(
            id: change.propertyId,
            parcelId: data["parcel_id"]?.value as? String ?? "",
            amount: data["amount"]?.value as? Double ?? 0,
            acreage: data["acreage"]?.value as? Double,
            pricePerAcre: data["price_per_acre"]?.value as? Double,
            waterScore: data["water_score"]?.value as? Double ?? 0,
            investmentScore: data["investment_score"]?.value as? Double,
            estimatedAllInCost: data["estimated_all_in_cost"]?.value as? Double,
            assessedValue: data["assessed_value"]?.value as? Double,
            assessedValueRatio: data["assessed_value_ratio"]?.value as? Double,
            description: data["description"]?.value as? String,
            county: data["county"]?.value as? String,
            ownerName: data["owner_name"]?.value as? String,
            yearSold: data["year_sold"]?.value as? String,
            rank: data["rank"]?.value as? Int32,
            createdAt: change.timestamp,
            updatedAt: change.timestamp,
            deviceId: change.deviceId,
            syncTimestamp: change.timestamp,
            isDeleted: change.operation == "delete"
        )
    }

    private func convertSyncConflictToAPIProperty(_ conflict: SyncConflict) throws -> APIProperty {
        let data = conflict.remoteData

        return APIProperty(
            id: conflict.propertyId,
            parcelId: data["parcel_id"]?.value as? String ?? "",
            amount: data["amount"]?.value as? Double ?? 0,
            acreage: data["acreage"]?.value as? Double,
            pricePerAcre: data["price_per_acre"]?.value as? Double,
            waterScore: data["water_score"]?.value as? Double ?? 0,
            investmentScore: data["investment_score"]?.value as? Double,
            estimatedAllInCost: data["estimated_all_in_cost"]?.value as? Double,
            assessedValue: data["assessed_value"]?.value as? Double,
            assessedValueRatio: data["assessed_value_ratio"]?.value as? Double,
            description: data["description"]?.value as? String,
            county: data["county"]?.value as? String,
            ownerName: data["owner_name"]?.value as? String,
            yearSold: data["year_sold"]?.value as? String,
            rank: data["rank"]?.value as? Int32,
            createdAt: conflict.remoteTimestamp,
            updatedAt: conflict.remoteTimestamp,
            deviceId: nil,
            syncTimestamp: conflict.remoteTimestamp,
            isDeleted: false
        )
    }

    // MARK: - Public Sync Methods

    /// Sync if needed (called when app becomes active or user pulls to refresh)
    func syncWithBackendIfNeeded() async {
        // Auto-sync if more than 15 minutes since last sync
        let needsSync = lastSyncDate?.timeIntervalSinceNow ?? -Double.infinity < -900

        if needsSync && hasNetworkConnection {
            await syncWithBackend()
        }
    }

    /// Manual sync triggered by user
    func manualSync() async {
        await syncWithBackend()
    }

    /// Create new property with backend sync
    func createProperty(
        parcelId: String,
        amount: Double,
        acreage: Double?,
        description: String?,
        county: String?,
        ownerName: String?,
        yearSold: String?,
        assessedValue: Double?
    ) async throws {

        // Create property locally first (offline-first approach)
        let context = persistenceController.container.viewContext
        let property = Property(context: context)
        property.parcelId = parcelId
        property.amount = amount
        property.acreage = acreage ?? 0
        property.propertyDescription = description
        property.county = county
        property.ownerName = ownerName
        property.yearSold = yearSold
        property.assessedValue = assessedValue ?? 0
        property.createdAt = Date()
        property.updatedAt = Date()

        // Calculate metrics locally
        calculateMetrics(for: property)

        // Save to Core Data
        try context.save()

        // Refresh local data
        loadProperties()

        // Sync with backend if online
        if hasNetworkConnection {
            do {
                let apiProperty = property.toAPICreateModel()
                let createdProperty = try await NetworkManager.shared.createProperty(apiProperty)

                // Update local property with server response (including any server-calculated fields)
                property.updateFromAPIModel(createdProperty, context: context)
                try context.save()

                print("✅ Property created and synced with backend")

            } catch {
                print("⚠️ Property created locally but sync failed: \(error)")
                // Property is still saved locally, will sync later
            }
        }
    }

    /// Update property with backend sync
    func updateProperty(_ property: Property) async throws {
        // Update locally first
        property.updatedAt = Date()
        calculateMetrics(for: property)
        try persistenceController.container.viewContext.save()

        // Refresh local data
        loadProperties()

        // Sync with backend if online
        if hasNetworkConnection {
            do {
                let apiProperty = property.toAPIModel()
                let updatedProperty = try await NetworkManager.shared.updateProperty(apiProperty)

                // Update with server response
                property.updateFromAPIModel(updatedProperty, context: persistenceController.container.viewContext)
                try persistenceController.container.viewContext.save()

                print("✅ Property updated and synced with backend")

            } catch {
                print("⚠️ Property updated locally but sync failed: \(error)")
                // Update is still saved locally, will sync later
            }
        }
    }

    /// Validate algorithm consistency with backend
    func validateAlgorithmConsistency(for property: Property) async -> Bool {
        guard hasNetworkConnection else { return true } // Can't validate offline

        do {
            return try await NetworkManager.shared.validateAlgorithmCompatibility(
                amount: property.amount,
                acreage: property.acreage > 0 ? property.acreage : nil,
                description: property.propertyDescription,
                assessedValue: property.assessedValue > 0 ? property.assessedValue : nil
            )
        } catch {
            print("⚠️ Algorithm validation failed: \(error)")
            return false
        }
    }

    /// Get network statistics
    func getNetworkStatistics() -> NetworkStatistics {
        return NetworkManager.shared.getNetworkStatistics()
    }

    /// Clear network cache and queue
    func clearNetworkCache() {
        NetworkManager.shared.clearRequestQueue()
        NetworkManager.shared.resetNetworkStatistics()
    }
}

// MARK: - Property Core Data Extension

extension Property {
    /// Flag to track if property needs update from server
    var needsUpdate: Bool {
        get {
            return primitiveValue(forKey: "needsUpdate") as? Bool ?? false
        }
        set {
            setPrimitiveValue(newValue, forKey: "needsUpdate")
        }
    }
}