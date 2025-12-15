//
//  Property+API.swift
//  AlabamaAuctionWatcher
//
//  Core Data Property extensions for API integration
//  Handles conversion between Core Data entities and API models
//

import Foundation
import CoreData

// MARK: - Property Core Data Extensions

extension Property {

    // MARK: - API Model Conversion

    /// Convert Core Data Property to APIProperty for network requests
    func toAPIModel() -> APIProperty {
        return APIProperty(
            id: objectID.uriRepresentation().absoluteString,
            parcelId: parcelId ?? "",
            amount: amount,
            acreage: acreage == 0 ? nil : acreage,
            pricePerAcre: pricePerAcre == 0 ? nil : pricePerAcre,
            waterScore: waterScore,
            investmentScore: investmentScore == 0 ? nil : investmentScore,
            estimatedAllInCost: estimatedAllInCost == 0 ? nil : estimatedAllInCost,
            assessedValue: assessedValue == 0 ? nil : assessedValue,
            assessedValueRatio: assessedValueRatio == 0 ? nil : assessedValueRatio,
            description: propertyDescription,
            county: county,
            ownerName: ownerName,
            yearSold: yearSold,
            rank: rank == 0 ? nil : rank,
            createdAt: createdAt?.toISO8601String(),
            updatedAt: updatedAt?.toISO8601String(),
            deviceId: nil, // Will be set by NetworkManager
            syncTimestamp: updatedAt?.toISO8601String(),
            isDeleted: false // Core Data entities are not deleted when fetched
        )
    }

    /// Create APIProperty for property creation (without ID and calculated fields)
    func toAPICreateModel() -> APIProperty {
        return APIProperty(
            id: nil,
            parcelId: parcelId ?? "",
            amount: amount,
            acreage: acreage == 0 ? nil : acreage,
            pricePerAcre: nil, // Will be calculated by backend
            waterScore: 0, // Will be calculated by backend
            investmentScore: nil, // Will be calculated by backend
            estimatedAllInCost: nil, // Will be calculated by backend
            assessedValue: assessedValue == 0 ? nil : assessedValue,
            assessedValueRatio: nil, // Will be calculated by backend
            description: propertyDescription,
            county: county,
            ownerName: ownerName,
            yearSold: yearSold,
            rank: nil, // Will be calculated by backend
            createdAt: nil,
            updatedAt: nil,
            deviceId: nil, // Will be set by NetworkManager
            syncTimestamp: nil,
            isDeleted: false
        )
    }

    /// Update Core Data Property from API response
    func updateFromAPIModel(_ apiProperty: APIProperty, context: NSManagedObjectContext) {
        // Update basic properties
        self.parcelId = apiProperty.parcelId
        self.amount = apiProperty.amount
        self.acreage = apiProperty.acreage ?? 0
        self.propertyDescription = apiProperty.description
        self.county = apiProperty.county
        self.ownerName = apiProperty.ownerName
        self.yearSold = apiProperty.yearSold
        self.assessedValue = apiProperty.assessedValue ?? 0

        // Update calculated properties (from backend algorithms)
        self.pricePerAcre = apiProperty.pricePerAcre ?? 0
        self.waterScore = apiProperty.waterScore
        self.investmentScore = apiProperty.investmentScore ?? 0
        self.estimatedAllInCost = apiProperty.estimatedAllInCost ?? 0
        self.assessedValueRatio = apiProperty.assessedValueRatio ?? 0
        self.rank = apiProperty.rank ?? 0

        // Update timestamps
        if let createdAtString = apiProperty.createdAt,
           let createdAt = Date.fromISO8601String(createdAtString) {
            self.createdAt = createdAt
        }

        if let updatedAtString = apiProperty.updatedAt,
           let updatedAt = Date.fromISO8601String(updatedAtString) {
            self.updatedAt = updatedAt
        } else {
            self.updatedAt = Date()
        }

        // Validate algorithm compatibility
        validateCalculatedFields(apiProperty)
    }

    /// Create new Core Data Property from API response
    static func createFromAPIModel(
        _ apiProperty: APIProperty,
        context: NSManagedObjectContext
    ) -> Property {
        let property = Property(context: context)
        property.updateFromAPIModel(apiProperty, context: context)

        // Set creation date if not provided
        if property.createdAt == nil {
            property.createdAt = Date()
        }

        return property
    }

    // MARK: - Validation

    /// Validate that calculated fields match local algorithm results
    private func validateCalculatedFields(_ apiProperty: APIProperty) {
        // Validate water score
        let localWaterScore = WaterFeatureDetector.calculateWaterScore(description: propertyDescription ?? "")
        let waterScoreDiff = abs(localWaterScore - apiProperty.waterScore)

        if waterScoreDiff > 0.1 {
            print("⚠️ Water score mismatch for property \(parcelId ?? "unknown"):")
            print("  Local: \(localWaterScore), API: \(apiProperty.waterScore), Diff: \(waterScoreDiff)")
        }

        // Validate investment score
        if let apiInvestmentScore = apiProperty.investmentScore,
           let apiPricePerAcre = apiProperty.pricePerAcre,
           let apiAssessedValueRatio = apiProperty.assessedValueRatio {

            let localInvestmentScore = InvestmentCalculator.calculateInvestmentScore(
                pricePerAcre: apiPricePerAcre,
                acreage: acreage,
                waterScore: localWaterScore,
                assessedValueRatio: apiAssessedValueRatio
            )

            let investmentScoreDiff = abs(localInvestmentScore - apiInvestmentScore)

            if investmentScoreDiff > 0.5 {
                print("⚠️ Investment score mismatch for property \(parcelId ?? "unknown"):")
                print("  Local: \(localInvestmentScore), API: \(apiInvestmentScore), Diff: \(investmentScoreDiff)")
            }
        }
    }

    // MARK: - Batch Operations

    /// Convert multiple Core Data properties to API models
    static func toAPIModels(_ properties: [Property]) -> [APIProperty] {
        return properties.map { $0.toAPIModel() }
    }

    /// Update multiple Core Data properties from API models
    static func updateFromAPIModels(
        _ apiProperties: [APIProperty],
        context: NSManagedObjectContext
    ) throws {
        for apiProperty in apiProperties {
            // Try to find existing property
            if let existingProperty = findProperty(by: apiProperty.parcelId, in: context) {
                existingProperty.updateFromAPIModel(apiProperty, context: context)
            } else {
                // Create new property
                _ = createFromAPIModel(apiProperty, context: context)
            }
        }

        // Save context
        try context.save()
    }

    /// Find property by parcel ID
    static func findProperty(by parcelId: String, in context: NSManagedObjectContext) -> Property? {
        let request: NSFetchRequest<Property> = Property.fetchRequest()
        request.predicate = NSPredicate(format: "parcelId == %@", parcelId)
        request.fetchLimit = 1

        return try? context.fetch(request).first
    }
}

// MARK: - Date Extensions

extension Date {

    /// Convert Date to ISO8601 string for API compatibility
    func toISO8601String() -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: self)
    }

    /// Create Date from ISO8601 string
    static func fromISO8601String(_ string: String) -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: string) ?? ISO8601DateFormatter().date(from: string)
    }
}

// MARK: - Property Change Tracking

extension Property {

    /// Create PropertyChange for sync operations
    func createPropertyChange(operation: String, deviceId: String) -> PropertyChange {
        let changeData: [String: AnyCodable]

        switch operation {
        case "create", "update":
            changeData = [
                "parcel_id": AnyCodable(parcelId),
                "amount": AnyCodable(amount),
                "acreage": AnyCodable(acreage),
                "description": AnyCodable(propertyDescription),
                "county": AnyCodable(county),
                "owner_name": AnyCodable(ownerName),
                "year_sold": AnyCodable(yearSold),
                "assessed_value": AnyCodable(assessedValue),
                "price_per_acre": AnyCodable(pricePerAcre),
                "water_score": AnyCodable(waterScore),
                "investment_score": AnyCodable(investmentScore),
                "estimated_all_in_cost": AnyCodable(estimatedAllInCost),
                "assessed_value_ratio": AnyCodable(assessedValueRatio),
                "rank": AnyCodable(rank)
            ]
        case "delete":
            changeData = [:]
        default:
            changeData = [:]
        }

        return PropertyChange(
            propertyId: objectID.uriRepresentation().absoluteString,
            operation: operation,
            data: changeData.isEmpty ? nil : changeData,
            timestamp: Date().toISO8601String(),
            deviceId: deviceId
        )
    }
}

// MARK: - Core Data Query Extensions

extension Property {

    /// Fetch properties that need to be synced (modified since last sync)
    static func fetchPropertiesForSync(
        since lastSyncDate: Date,
        context: NSManagedObjectContext
    ) throws -> [Property] {
        let request: NSFetchRequest<Property> = Property.fetchRequest()
        request.predicate = NSPredicate(format: "updatedAt > %@", lastSyncDate as NSDate)
        request.sortDescriptors = [NSSortDescriptor(keyPath: \Property.updatedAt, ascending: true)]

        return try context.fetch(request)
    }

    /// Fetch properties with conflicts (same parcel ID but different update times)
    static func fetchConflictingProperties(
        for apiProperties: [APIProperty],
        context: NSManagedObjectContext
    ) throws -> [(local: Property, remote: APIProperty)] {
        var conflicts: [(local: Property, remote: APIProperty)] = []

        for apiProperty in apiProperties {
            if let localProperty = findProperty(by: apiProperty.parcelId, in: context),
               let remoteUpdateString = apiProperty.updatedAt,
               let remoteUpdateDate = Date.fromISO8601String(remoteUpdateString),
               let localUpdateDate = localProperty.updatedAt {

                // Check if timestamps differ significantly (more than 1 second)
                let timeDiff = abs(localUpdateDate.timeIntervalSince(remoteUpdateDate))
                if timeDiff > 1.0 {
                    conflicts.append((local: localProperty, remote: apiProperty))
                }
            }
        }

        return conflicts
    }

    /// Get properties count by county for analytics
    static func getCountByCounty(context: NSManagedObjectContext) throws -> [String: Int] {
        let request: NSFetchRequest<Property> = Property.fetchRequest()

        let properties = try context.fetch(request)
        var countByCounty: [String: Int] = [:]

        for property in properties {
            let county = property.county ?? "Unknown"
            countByCounty[county, default: 0] += 1
        }

        return countByCounty
    }
}

// MARK: - Algorithm Compatibility

extension Property {

    /// Recalculate all metrics using local algorithms and compare with stored values
    func validateAlgorithmConsistency() -> (isConsistent: Bool, issues: [String]) {
        var issues: [String] = []

        // Validate water score
        let calculatedWaterScore = WaterFeatureDetector.calculateWaterScore(description: propertyDescription ?? "")
        if abs(calculatedWaterScore - waterScore) > 0.1 {
            issues.append("Water score mismatch: stored \(waterScore), calculated \(calculatedWaterScore)")
        }

        // Validate price per acre
        if acreage > 0 {
            let calculatedPricePerAcre = amount / acreage
            if abs(calculatedPricePerAcre - pricePerAcre) > 0.01 {
                issues.append("Price per acre mismatch: stored \(pricePerAcre), calculated \(calculatedPricePerAcre)")
            }
        }

        // Validate assessed value ratio
        if assessedValue > 0 {
            let calculatedRatio = amount / assessedValue
            if abs(calculatedRatio - assessedValueRatio) > 0.01 {
                issues.append("Assessed value ratio mismatch: stored \(assessedValueRatio), calculated \(calculatedRatio)")
            }
        }

        // Validate investment score
        let calculatedInvestmentScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: pricePerAcre,
            acreage: acreage,
            waterScore: calculatedWaterScore,
            assessedValueRatio: assessedValueRatio
        )

        if abs(calculatedInvestmentScore - investmentScore) > 0.5 {
            issues.append("Investment score mismatch: stored \(investmentScore), calculated \(calculatedInvestmentScore)")
        }

        return (isConsistent: issues.isEmpty, issues: issues)
    }

    /// Recalculate all metrics using local algorithms
    func recalculateMetrics() {
        // Recalculate water score
        waterScore = WaterFeatureDetector.calculateWaterScore(description: propertyDescription ?? "")

        // Recalculate price per acre
        if acreage > 0 {
            pricePerAcre = amount / acreage
        } else {
            pricePerAcre = 0
        }

        // Recalculate assessed value ratio
        if assessedValue > 0 {
            assessedValueRatio = amount / assessedValue
        } else {
            assessedValueRatio = 0
        }

        // Recalculate investment score
        investmentScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: pricePerAcre,
            acreage: acreage,
            waterScore: waterScore,
            assessedValueRatio: assessedValueRatio
        )

        // Recalculate estimated all-in cost
        estimatedAllInCost = InvestmentCalculator.calculateEstimatedAllInCost(amount: amount)

        // Update timestamp
        updatedAt = Date()
    }
}