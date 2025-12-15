//
//  County+API.swift
//  AlabamaAuctionWatcher
//
//  County Core Data extensions for API integration
//  Handles Alabama county validation and API communication
//

import Foundation
import CoreData

// MARK: - API Models for County Operations

struct APICounty: Codable {
    let code: String
    let name: String
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case code
        case name
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct CountyListResponse: Codable {
    let counties: [APICounty]
    let totalCount: Int

    enum CodingKeys: String, CodingKey {
        case counties
        case totalCount = "total_count"
    }
}

struct CountyValidationRequest: Codable {
    let code: String?
    let name: String?
}

struct CountyValidationResponse: Codable {
    let isValid: Bool
    let code: String?
    let name: String?
    let errorMessage: String?

    enum CodingKeys: String, CodingKey {
        case isValid = "is_valid"
        case code
        case name
        case errorMessage = "error_message"
    }
}

// MARK: - County Core Data Extensions

extension County {

    // MARK: - API Model Conversion

    /// Convert Core Data County to APICounty for network requests
    func toAPIModel() -> APICounty {
        return APICounty(
            code: code ?? "",
            name: name ?? "",
            createdAt: createdAt?.toISO8601String(),
            updatedAt: updatedAt?.toISO8601String()
        )
    }

    /// Update Core Data County from API response
    func updateFromAPIModel(_ apiCounty: APICounty, context: NSManagedObjectContext) {
        self.code = apiCounty.code
        self.name = apiCounty.name

        // Update timestamps
        if let createdAtString = apiCounty.createdAt,
           let createdAt = Date.fromISO8601String(createdAtString) {
            self.createdAt = createdAt
        }

        if let updatedAtString = apiCounty.updatedAt,
           let updatedAt = Date.fromISO8601String(updatedAtString) {
            self.updatedAt = updatedAt
        } else {
            self.updatedAt = Date()
        }
    }

    /// Create new Core Data County from API response
    static func createFromAPIModel(
        _ apiCounty: APICounty,
        context: NSManagedObjectContext
    ) -> County {
        let county = County(context: context)
        county.updateFromAPIModel(apiCounty, context: context)

        // Set creation date if not provided
        if county.createdAt == nil {
            county.createdAt = Date()
        }

        return county
    }

    // MARK: - Batch Operations

    /// Update multiple Core Data counties from API models
    static func updateFromAPIModels(
        _ apiCounties: [APICounty],
        context: NSManagedObjectContext
    ) throws {
        for apiCounty in apiCounties {
            // Try to find existing county
            if let existingCounty = findCounty(by: apiCounty.code, in: context) {
                existingCounty.updateFromAPIModel(apiCounty, context: context)
            } else {
                // Create new county
                _ = createFromAPIModel(apiCounty, context: context)
            }
        }

        // Save context
        try context.save()
    }

    /// Find county by code
    static func findCounty(by code: String, in context: NSManagedObjectContext) -> County? {
        let request: NSFetchRequest<County> = County.fetchRequest()
        request.predicate = NSPredicate(format: "code == %@", code)
        request.fetchLimit = 1

        return try? context.fetch(request).first
    }

    /// Find county by name
    static func findCounty(byName name: String, in context: NSManagedObjectContext) -> County? {
        let request: NSFetchRequest<County> = County.fetchRequest()
        request.predicate = NSPredicate(format: "name == %@", name)
        request.fetchLimit = 1

        return try? context.fetch(request).first
    }
}

// MARK: - Alabama County Validation

extension County {

    /// Validate Alabama county code against ADOR mapping
    static func validateADORCode(_ code: String) -> Bool {
        // Validate format (2-digit string)
        guard code.count == 2, let codeInt = Int(code) else {
            return false
        }

        // Validate range (01-67)
        return codeInt >= 1 && codeInt <= 67
    }

    /// Validate Alabama county name
    static func validateCountyName(_ name: String) -> Bool {
        return CountyValidator.isValidCounty(name)
    }

    /// Get ADOR code for county name
    static func getADORCode(for countyName: String) -> String? {
        return CountyValidator.getCountyCode(for: countyName)
    }

    /// Get county name for ADOR code
    static func getCountyName(for code: String) -> String? {
        return CountyValidator.getCountyName(for: code)
    }

    /// Initialize all 67 Alabama counties in Core Data
    static func initializeAlabamaCounties(context: NSManagedObjectContext) throws {
        // Check if counties already exist
        let existingCount = try getCountyCount(context: context)
        if existingCount >= 67 {
            print("✅ Alabama counties already initialized (\(existingCount) counties)")
            return
        }

        // Get all Alabama counties from CountyValidator
        let alabamaCounties = CountyValidator.getAllCounties()

        for (code, name) in alabamaCounties {
            // Check if county already exists
            if findCounty(by: code, in: context) == nil {
                let county = County(context: context)
                county.code = code
                county.name = name
                county.createdAt = Date()
                county.updatedAt = Date()
            }
        }

        try context.save()
        print("✅ Initialized \(alabamaCounties.count) Alabama counties in Core Data")
    }

    /// Get count of counties in Core Data
    static func getCountyCount(context: NSManagedObjectContext) throws -> Int {
        let request: NSFetchRequest<County> = County.fetchRequest()
        return try context.count(for: request)
    }

    /// Get all counties sorted by name
    static func getAllCounties(context: NSManagedObjectContext) throws -> [County] {
        let request: NSFetchRequest<County> = County.fetchRequest()
        request.sortDescriptors = [NSSortDescriptor(keyPath: \County.name, ascending: true)]
        return try context.fetch(request)
    }

    /// Search counties by partial name (for autocomplete)
    static func searchCounties(
        partialName: String,
        context: NSManagedObjectContext
    ) throws -> [County] {
        let request: NSFetchRequest<County> = County.fetchRequest()
        request.predicate = NSPredicate(format: "name CONTAINS[cd] %@", partialName)
        request.sortDescriptors = [NSSortDescriptor(keyPath: \County.name, ascending: true)]
        request.fetchLimit = 10 // Limit for autocomplete

        return try context.fetch(request)
    }
}

// MARK: - County Statistics

extension County {

    /// Get property count for this county
    func getPropertyCount(context: NSManagedObjectContext) throws -> Int {
        let request: NSFetchRequest<Property> = Property.fetchRequest()
        request.predicate = NSPredicate(format: "county == %@", name ?? "")
        return try context.count(for: request)
    }

    /// Get average investment score for properties in this county
    func getAverageInvestmentScore(context: NSManagedObjectContext) throws -> Double {
        let request: NSFetchRequest<Property> = Property.fetchRequest()
        request.predicate = NSPredicate(format: "county == %@ AND investmentScore > 0", name ?? "")

        let properties = try context.fetch(request)
        guard !properties.isEmpty else { return 0.0 }

        let totalScore = properties.reduce(0.0) { $0 + $1.investmentScore }
        return totalScore / Double(properties.count)
    }

    /// Get county statistics
    func getStatistics(context: NSManagedObjectContext) throws -> CountyStatistics {
        let propertyCount = try getPropertyCount(context: context)
        let avgInvestmentScore = try getAverageInvestmentScore(context: context)

        return CountyStatistics(
            code: code ?? "",
            name: name ?? "",
            propertyCount: propertyCount,
            averageInvestmentScore: avgInvestmentScore
        )
    }

    /// Get statistics for all counties
    static func getAllCountyStatistics(context: NSManagedObjectContext) throws -> [CountyStatistics] {
        let counties = try getAllCounties(context: context)
        return try counties.map { try $0.getStatistics(context: context) }
    }
}

// MARK: - County Statistics Model

struct CountyStatistics {
    let code: String
    let name: String
    let propertyCount: Int
    let averageInvestmentScore: Double
}

// MARK: - NetworkManager County Extensions

extension NetworkManager {

    /// Fetch all counties from API
    func fetchCounties() async throws -> CountyListResponse {
        guard let url = URL(string: "\(baseURL)/counties") else {
            throw NetworkError.invalidURL
        }

        return try await performRequest(url: url, requiresAuth: false)
    }

    /// Validate county with API
    func validateCounty(code: String?, name: String?) async throws -> CountyValidationResponse {
        guard let url = URL(string: "\(baseURL)/counties/validate") else {
            throw NetworkError.invalidURL
        }

        let validationRequest = CountyValidationRequest(code: code, name: name)

        return try await performRequest(
            url: url,
            method: "POST",
            body: validationRequest,
            requiresAuth: false
        )
    }

    /// Search counties with autocomplete
    func searchCounties(query: String) async throws -> [APICounty] {
        guard let url = URL(string: "\(baseURL)/counties/search/autocomplete?query=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")") else {
            throw NetworkError.invalidURL
        }

        struct AutocompleteResponse: Codable {
            let suggestions: [AutocompleteSuggestion]
        }

        struct AutocompleteSuggestion: Codable {
            let code: String
            let name: String
            let displayText: String

            enum CodingKeys: String, CodingKey {
                case code
                case name
                case displayText = "display_text"
            }
        }

        let response: AutocompleteResponse = try await performRequest(
            url: url,
            requiresAuth: false
        )

        return response.suggestions.map { suggestion in
            APICounty(
                code: suggestion.code,
                name: suggestion.name,
                createdAt: nil,
                updatedAt: nil
            )
        }
    }

    /// Sync counties with API (update local Core Data)
    func syncCounties(context: NSManagedObjectContext) async throws {
        let response = try await fetchCounties()

        // Update Core Data with API response
        try County.updateFromAPIModels(response.counties, context: context)

        print("✅ Synced \(response.counties.count) counties from API")
    }
}

// MARK: - County Picker Support

extension County {

    /// Get display name for county picker
    var displayName: String {
        guard let name = name, let code = code else {
            return "Unknown County"
        }
        return "\(name) (\(code))"
    }

    /// Get counties for picker (sorted by name)
    static func getCountiesForPicker(context: NSManagedObjectContext) throws -> [County] {
        let request: NSFetchRequest<County> = County.fetchRequest()
        request.sortDescriptors = [NSSortDescriptor(keyPath: \County.name, ascending: true)]
        return try context.fetch(request)
    }

    /// Get county names for picker (strings only)
    static func getCountyNamesForPicker(context: NSManagedObjectContext) throws -> [String] {
        let counties = try getCountiesForPicker(context: context)
        return counties.compactMap { $0.name }
    }
}