//
//  NetworkManager.swift
//  AlabamaAuctionWatcher
//
//  Phase 2A Week 3-4: Data Synchronization & API Integration
//  Comprehensive networking layer for FastAPI backend communication
//

import Foundation
import Network
import UIKit

// MARK: - API Models

struct APIProperty: Codable {
    let id: String?
    let parcelId: String
    let amount: Double
    let acreage: Double?
    let pricePerAcre: Double?
    let waterScore: Double
    let investmentScore: Double?
    let estimatedAllInCost: Double?
    let assessedValue: Double?
    let assessedValueRatio: Double?
    let description: String?
    let county: String?
    let ownerName: String?
    let yearSold: String?
    let rank: Int32?
    let createdAt: String?
    let updatedAt: String?
    let deviceId: String?
    let syncTimestamp: String?
    let isDeleted: Bool

    enum CodingKeys: String, CodingKey {
        case id, parcelId = "parcel_id", amount, acreage
        case pricePerAcre = "price_per_acre"
        case waterScore = "water_score"
        case investmentScore = "investment_score"
        case estimatedAllInCost = "estimated_all_in_cost"
        case assessedValue = "assessed_value"
        case assessedValueRatio = "assessed_value_ratio"
        case description, county
        case ownerName = "owner_name"
        case yearSold = "year_sold"
        case rank
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case deviceId = "device_id"
        case syncTimestamp = "sync_timestamp"
        case isDeleted = "is_deleted"
    }
}

struct PropertyListResponse: Codable {
    let properties: [APIProperty]
    let totalCount: Int
    let page: Int
    let pageSize: Int
    let totalPages: Int
    let hasNext: Bool
    let hasPrevious: Bool

    enum CodingKeys: String, CodingKey {
        case properties
        case totalCount = "total_count"
        case page
        case pageSize = "page_size"
        case totalPages = "total_pages"
        case hasNext = "has_next"
        case hasPrevious = "has_previous"
    }
}

struct APIKeyResponse: Codable {
    let apiKey: String
    let deviceId: String
    let createdAt: String
    let scopes: [String]
    let usageInstructions: String

    enum CodingKeys: String, CodingKey {
        case apiKey = "api_key"
        case deviceId = "device_id"
        case createdAt = "created_at"
        case scopes
        case usageInstructions = "usage_instructions"
    }
}

struct DeltaSyncRequest: Codable {
    let deviceId: String
    let lastSyncTimestamp: String
    let changes: [PropertyChange]
    let algorithmVersion: String
    let appVersion: String

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case lastSyncTimestamp = "last_sync_timestamp"
        case changes
        case algorithmVersion = "algorithm_version"
        case appVersion = "app_version"
    }
}

struct PropertyChange: Codable {
    let propertyId: String
    let operation: String
    let data: [String: AnyCodable]?
    let timestamp: String
    let deviceId: String

    enum CodingKeys: String, CodingKey {
        case propertyId = "property_id"
        case operation
        case data
        case timestamp
        case deviceId = "device_id"
    }
}

struct DeltaSyncResponse: Codable {
    let serverChanges: [PropertyChange]
    let conflicts: [SyncConflict]
    let newSyncTimestamp: String
    let syncStatus: String
    let changesApplied: Int
    let changesRejected: Int
    let serverChangesCount: Int
    let conflictsCount: Int
    let algorithmCompatibility: Bool
    let algorithmValidationMessage: String?

    enum CodingKeys: String, CodingKey {
        case serverChanges = "server_changes"
        case conflicts
        case newSyncTimestamp = "new_sync_timestamp"
        case syncStatus = "sync_status"
        case changesApplied = "changes_applied"
        case changesRejected = "changes_rejected"
        case serverChangesCount = "server_changes_count"
        case conflictsCount = "conflicts_count"
        case algorithmCompatibility = "algorithm_compatibility"
        case algorithmValidationMessage = "algorithm_validation_message"
    }
}

struct SyncConflict: Codable {
    let propertyId: String
    let localTimestamp: String
    let remoteTimestamp: String
    let localData: [String: AnyCodable]
    let remoteData: [String: AnyCodable]
    let conflictFields: [String]

    enum CodingKeys: String, CodingKey {
        case propertyId = "property_id"
        case localTimestamp = "local_timestamp"
        case remoteTimestamp = "remote_timestamp"
        case localData = "local_data"
        case remoteData = "remote_data"
        case conflictFields = "conflict_fields"
    }
}

// MARK: - AnyCodable Helper

struct AnyCodable: Codable {
    let value: Any

    init<T>(_ value: T?) {
        self.value = value ?? ()
    }
}

extension AnyCodable {
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if container.decodeNil() {
            self.init(())
        } else if let bool = try? container.decode(Bool.self) {
            self.init(bool)
        } else if let int = try? container.decode(Int.self) {
            self.init(int)
        } else if let double = try? container.decode(Double.self) {
            self.init(double)
        } else if let string = try? container.decode(String.self) {
            self.init(string)
        } else if let array = try? container.decode([AnyCodable].self) {
            self.init(array.map { $0.value })
        } else if let dictionary = try? container.decode([String: AnyCodable].self) {
            self.init(dictionary.mapValues { $0.value })
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "AnyCodable value cannot be decoded")
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch value {
        case is Void:
            try container.encodeNil()
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        case let array as [Any]:
            try container.encode(array.map(AnyCodable.init))
        case let dictionary as [String: Any]:
            try container.encode(dictionary.mapValues(AnyCodable.init))
        default:
            let context = EncodingError.Context(codingPath: container.codingPath, debugDescription: "AnyCodable value cannot be encoded")
            throw EncodingError.invalidValue(value, context)
        }
    }
}

// MARK: - Network Error Types

enum NetworkError: Error, LocalizedError {
    case invalidURL
    case noData
    case decodingError(String)
    case serverError(Int, String)
    case authenticationFailed
    case networkUnavailable
    case timeout
    case algorithmMismatch(String)
    case syncConflict([SyncConflict])

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .noData:
            return "No data received"
        case .decodingError(let message):
            return "Data decoding failed: \(message)"
        case .serverError(let code, let message):
            return "Server error \(code): \(message)"
        case .authenticationFailed:
            return "Authentication failed"
        case .networkUnavailable:
            return "Network unavailable"
        case .timeout:
            return "Request timeout"
        case .algorithmMismatch(let message):
            return "Algorithm compatibility error: \(message)"
        case .syncConflict(let conflicts):
            return "Sync conflicts detected: \(conflicts.count) properties"
        }
    }
}

// MARK: - NetworkManager Class

@MainActor
class NetworkManager: ObservableObject {
    static let shared = NetworkManager()

    // MARK: - Configuration

    private let baseURL = "http://localhost:8000/api/v1" // Change for production
    private let session: URLSession
    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "NetworkMonitor")

    // MARK: - Published Properties

    @Published var isConnected = true
    @Published var isLoading = false
    @Published var lastSyncDate: Date?
    @Published var apiKeyStatus: String = "Not configured"

    // MARK: - Private Properties

    private var apiKey: String?
    private var deviceId: String
    private let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0"
    private let algorithmVersion = "1.0.0" // Must match backend validation

    // MARK: - Initialization

    private init() {
        // Configure URL session with timeout and caching
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30.0
        config.timeoutIntervalForResource = 60.0
        config.requestCachePolicy = .reloadIgnoringLocalCacheData

        self.session = URLSession(configuration: config)

        // Get or create device ID
        if let existingDeviceId = UserDefaults.standard.string(forKey: "deviceId") {
            self.deviceId = existingDeviceId
        } else {
            self.deviceId = UUID().uuidString
            UserDefaults.standard.set(self.deviceId, forKey: "deviceId")
        }

        // Load stored API key
        self.apiKey = UserDefaults.standard.string(forKey: "apiKey")

        setupNetworkMonitoring()
        updateAPIKeyStatus()
    }

    // MARK: - Network Monitoring

    private func setupNetworkMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isConnected = path.status == .satisfied
            }
        }
        monitor.start(queue: monitorQueue)
    }

    // MARK: - Authentication

    func createAPIKey() async throws {
        isLoading = true
        defer { isLoading = false }

        guard let url = URL(string: "\(baseURL)/auth/device/api-key") else {
            throw NetworkError.invalidURL
        }

        let requestBody = [
            "device_id": deviceId,
            "app_version": appVersion,
            "device_name": UIDevice.current.name
        ]

        let response: APIKeyResponse = try await performRequest(
            url: url,
            method: "POST",
            body: requestBody,
            requiresAuth: false
        )

        // Store API key
        self.apiKey = response.apiKey
        UserDefaults.standard.set(response.apiKey, forKey: "apiKey")

        updateAPIKeyStatus()

        print("✅ API Key created successfully for device: \(deviceId)")
    }

    private func updateAPIKeyStatus() {
        if apiKey != nil {
            apiKeyStatus = "Configured"
        } else {
            apiKeyStatus = "Not configured"
        }
    }

    // MARK: - Retry Manager

    private static let retryManager = NetworkRetryManager()

    // MARK: - Generic Request Method

    private func performRequest<T: Codable>(
        url: URL,
        method: String = "GET",
        body: Encodable? = nil,
        requiresAuth: Bool = true,
        retryPolicy: RetryPolicy = .exponentialBackoff(.default),
        priority: QueuedRequest.RequestPriority = .normal
    ) async throws -> T {

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add authentication
        if requiresAuth {
            guard let apiKey = apiKey else {
                throw NetworkError.authenticationFailed
            }
            request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }

        // Add request body
        if let body = body {
            do {
                let encoder = JSONEncoder()
                encoder.dateEncodingStrategy = .iso8601
                request.httpBody = try encoder.encode(body)
            } catch {
                throw NetworkError.decodingError("Failed to encode request body: \(error.localizedDescription)")
            }
        }

        // Perform request with retry logic
        let data = try await Self.retryManager.performRequest(
            request,
            retryPolicy: retryPolicy,
            priority: priority
        )

        // Decode response
        do {
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            return try decoder.decode(T.self, from: data)
        } catch {
            throw NetworkError.decodingError("Failed to decode response: \(error.localizedDescription)")
        }
    }

    // MARK: - Property Operations

    func fetchProperties(
        county: String? = nil,
        minPrice: Double? = nil,
        maxPrice: Double? = nil,
        page: Int = 1,
        pageSize: Int = 100
    ) async throws -> PropertyListResponse {

        var components = URLComponents(string: "\(baseURL)/properties")!
        var queryItems: [URLQueryItem] = []

        if let county = county {
            queryItems.append(URLQueryItem(name: "county", value: county))
        }
        if let minPrice = minPrice {
            queryItems.append(URLQueryItem(name: "min_price", value: "\(minPrice)"))
        }
        if let maxPrice = maxPrice {
            queryItems.append(URLQueryItem(name: "max_price", value: "\(maxPrice)"))
        }
        queryItems.append(URLQueryItem(name: "page", value: "\(page)"))
        queryItems.append(URLQueryItem(name: "page_size", value: "\(pageSize)"))

        components.queryItems = queryItems

        guard let url = components.url else {
            throw NetworkError.invalidURL
        }

        return try await performRequest(
            url: url,
            retryPolicy: .forOperation(.read),
            priority: .normal
        )
    }

    func createProperty(_ property: APIProperty) async throws -> APIProperty {
        guard let url = URL(string: "\(baseURL)/properties") else {
            throw NetworkError.invalidURL
        }

        return try await performRequest(
            url: url,
            method: "POST",
            body: property,
            retryPolicy: .forOperation(.create),
            priority: .high
        )
    }

    func updateProperty(_ property: APIProperty) async throws -> APIProperty {
        guard let propertyId = property.id,
              let url = URL(string: "\(baseURL)/properties/\(propertyId)") else {
            throw NetworkError.invalidURL
        }

        return try await performRequest(
            url: url,
            method: "PUT",
            body: property,
            retryPolicy: .forOperation(.update),
            priority: .high
        )
    }

    func deleteProperty(id: String) async throws {
        guard let url = URL(string: "\(baseURL)/properties/\(id)") else {
            throw NetworkError.invalidURL
        }

        struct EmptyResponse: Codable {}

        let _: EmptyResponse = try await performRequest(
            url: url,
            method: "DELETE",
            retryPolicy: .forOperation(.delete),
            priority: .high
        )
    }

    // MARK: - Synchronization Operations

    func performDeltaSync(lastSyncTimestamp: Date, changes: [PropertyChange] = []) async throws -> DeltaSyncResponse {
        guard let url = URL(string: "\(baseURL)/sync/delta") else {
            throw NetworkError.invalidURL
        }

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        let syncRequest = DeltaSyncRequest(
            deviceId: deviceId,
            lastSyncTimestamp: formatter.string(from: lastSyncTimestamp),
            changes: changes,
            algorithmVersion: algorithmVersion,
            appVersion: appVersion
        )

        let response: DeltaSyncResponse = try await performRequest(
            url: url,
            method: "POST",
            body: syncRequest,
            retryPolicy: .forOperation(.sync),
            priority: .critical
        )

        // Check for algorithm compatibility
        if !response.algorithmCompatibility {
            throw NetworkError.algorithmMismatch(response.algorithmValidationMessage ?? "Unknown compatibility issue")
        }

        // Check for conflicts
        if !response.conflicts.isEmpty {
            throw NetworkError.syncConflict(response.conflicts)
        }

        // Update last sync date
        if let newSyncDate = formatter.date(from: response.newSyncTimestamp) {
            self.lastSyncDate = newSyncDate
            UserDefaults.standard.set(newSyncDate, forKey: "lastSyncDate")
        }

        return response
    }

    func performFullSync() async throws -> [APIProperty] {
        guard let url = URL(string: "\(baseURL)/sync/full") else {
            throw NetworkError.invalidURL
        }

        let syncRequest = [
            "device_id": deviceId,
            "algorithm_version": algorithmVersion,
            "app_version": appVersion,
            "include_deleted": false
        ] as [String: Any]

        struct FullSyncResponse: Codable {
            let allProperties: [APIProperty]
            let syncTimestamp: String
            let totalProperties: Int
            let algorithmCompatibility: Bool

            enum CodingKeys: String, CodingKey {
                case allProperties = "all_properties"
                case syncTimestamp = "sync_timestamp"
                case totalProperties = "total_properties"
                case algorithmCompatibility = "algorithm_compatibility"
            }
        }

        let response: FullSyncResponse = try await performRequest(
            url: url,
            method: "POST",
            body: syncRequest,
            retryPolicy: .forOperation(.sync),
            priority: .critical
        )

        // Check for algorithm compatibility
        if !response.algorithmCompatibility {
            throw NetworkError.algorithmMismatch("Algorithm compatibility check failed")
        }

        // Update last sync date
        let formatter = ISO8601DateFormatter()
        if let newSyncDate = formatter.date(from: response.syncTimestamp) {
            self.lastSyncDate = newSyncDate
            UserDefaults.standard.set(newSyncDate, forKey: "lastSyncDate")
        }

        return response.allProperties
    }

    // MARK: - Algorithm Validation

    func validateAlgorithmCompatibility(amount: Double, acreage: Double?, description: String?, assessedValue: Double?) async throws -> Bool {
        guard let url = URL(string: "\(baseURL)/properties/calculate") else {
            throw NetworkError.invalidURL
        }

        let calculationRequest = [
            "amount": amount,
            "acreage": acreage as Any,
            "description": description as Any,
            "assessed_value": assessedValue as Any
        ]

        struct CalculationResponse: Codable {
            let pricePerAcre: Double?
            let waterScore: Double
            let investmentScore: Double?
            let estimatedAllInCost: Double
            let assessedValueRatio: Double?
            let algorithmVersion: String

            enum CodingKeys: String, CodingKey {
                case pricePerAcre = "price_per_acre"
                case waterScore = "water_score"
                case investmentScore = "investment_score"
                case estimatedAllInCost = "estimated_all_in_cost"
                case assessedValueRatio = "assessed_value_ratio"
                case algorithmVersion = "algorithm_version"
            }
        }

        let response: CalculationResponse = try await performRequest(
            url: url,
            method: "POST",
            body: calculationRequest,
            retryPolicy: .forOperation(.read),
            priority: .normal
        )

        // Compare with local iOS calculation
        let localWaterScore = WaterFeatureDetector.calculateWaterScore(description: description ?? "")
        let localInvestmentScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: response.pricePerAcre ?? 0,
            acreage: acreage ?? 0,
            waterScore: localWaterScore,
            assessedValueRatio: response.assessedValueRatio ?? 0
        )

        // Check compatibility within tolerance
        let waterScoreDiff = abs(localWaterScore - response.waterScore)
        let investmentScoreDiff = abs(localInvestmentScore - (response.investmentScore ?? 0))

        let isCompatible = waterScoreDiff < 0.1 && investmentScoreDiff < 0.5

        if !isCompatible {
            print("⚠️ Algorithm mismatch detected:")
            print("  Water Score - Local: \(localWaterScore), Backend: \(response.waterScore), Diff: \(waterScoreDiff)")
            print("  Investment Score - Local: \(localInvestmentScore), Backend: \(response.investmentScore ?? 0), Diff: \(investmentScoreDiff)")
        }

        return isCompatible
    }

    // MARK: - Health Check

    func performHealthCheck() async throws -> Bool {
        guard let url = URL(string: "\(baseURL)/../health") else {
            throw NetworkError.invalidURL
        }

        struct HealthResponse: Codable {
            let status: String
        }

        let response: HealthResponse = try await performRequest(
            url: url,
            requiresAuth: false,
            retryPolicy: .forOperation(.healthCheck),
            priority: .low
        )

        return response.status == "healthy"
    }
}

// MARK: - UserDefaults Extension

extension UserDefaults {
    func date(forKey key: String) -> Date? {
        return object(forKey: key) as? Date
    }

    func set(_ date: Date?, forKey key: String) {
        set(date, forKey: key)
    }
}