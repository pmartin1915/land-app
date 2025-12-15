import XCTest
@testable import AlabamaAuctionWatcher

final class WaterFeatureDetectorTests: XCTestCase {

    func testWaterFeatureKeywordsStructure() {
        // Verify keyword arrays match Python implementation
        XCTAssertEqual(WaterFeatureKeywords.primary, ["creek", "stream", "river", "lake", "pond", "spring"])
        XCTAssertEqual(WaterFeatureKeywords.secondary, ["branch", "run", "brook", "tributary", "wetland", "marsh"])
        XCTAssertEqual(WaterFeatureKeywords.tertiary, ["water", "aquatic", "riparian", "shore", "bank", "waterfront"])

        // Verify weights match Python implementation
        XCTAssertEqual(WaterFeatureKeywords.weights.primary, 3.0)
        XCTAssertEqual(WaterFeatureKeywords.weights.secondary, 2.0)
        XCTAssertEqual(WaterFeatureKeywords.weights.tertiary, 1.0)
    }

    func testPrimaryKeywordDetection() {
        let descriptions = [
            "Property with creek access",
            "Beautiful stream frontage",
            "Large river on property",
            "Private lake included",
            "Natural pond on site",
            "Fresh water spring"
        ]

        for description in descriptions {
            let score = WaterFeatureDetector.calculateWaterScore(description: description)
            XCTAssertEqual(score, 3.0, accuracy: 0.01, "Primary keyword should score 3.0 points: \(description)")
        }
    }

    func testSecondaryKeywordDetection() {
        let descriptions = [
            "Property near branch",
            "Small run through property",
            "Beautiful brook nearby",
            "Tributary access available",
            "Wetland preservation area",
            "Marsh ecosystem present"
        ]

        for description in descriptions {
            let score = WaterFeatureDetector.calculateWaterScore(description: description)
            XCTAssertEqual(score, 2.0, accuracy: 0.01, "Secondary keyword should score 2.0 points: \(description)")
        }
    }

    func testTertiaryKeywordDetection() {
        let descriptions = [
            "Water available on property",
            "Aquatic habitat nearby",
            "Riparian zone included",
            "Beautiful shore access",
            "Creek bank property",
            "Waterfront location"
        ]

        for description in descriptions {
            let score = WaterFeatureDetector.calculateWaterScore(description: description)
            XCTAssertEqual(score, 1.0, accuracy: 0.01, "Tertiary keyword should score 1.0 points: \(description)")
        }
    }

    func testMultipleKeywordAccumulation() {
        // Test multiple keywords from same tier
        let multipleCreeks = "Property has creek and another creek"
        let score1 = WaterFeatureDetector.calculateWaterScore(description: multipleCreeks)
        XCTAssertEqual(score1, 6.0, accuracy: 0.01, "Multiple occurrences of same keyword should accumulate")

        // Test keywords from different tiers
        let mixedFeatures = "Beautiful creek frontage with water access and shore views"
        let score2 = WaterFeatureDetector.calculateWaterScore(description: mixedFeatures)
        // creek (3.0) + water (1.0) + shore (1.0) = 5.0
        XCTAssertEqual(score2, 5.0, accuracy: 0.01, "Mixed tier keywords should accumulate correctly")
    }

    func testCaseInsensitiveDetection() {
        let descriptions = [
            "CREEK FRONTAGE",
            "Stream Access",
            "beautiful POND nearby",
            "WATER features available"
        ]

        let expectedScores = [3.0, 3.0, 3.0, 1.0]

        for (index, description) in descriptions.enumerated() {
            let score = WaterFeatureDetector.calculateWaterScore(description: description)
            XCTAssertEqual(score, expectedScores[index], accuracy: 0.01, "Detection should be case insensitive: \(description)")
        }
    }

    func testNoWaterFeatures() {
        let descriptions = [
            "Dry land property",
            "Mountain property with great views",
            "Agricultural land for farming",
            "Residential lot in subdivision",
            ""
        ]

        for description in descriptions {
            let score = WaterFeatureDetector.calculateWaterScore(description: description)
            XCTAssertEqual(score, 0.0, "Properties without water keywords should score 0.0: \(description)")
        }
    }

    func testEmptyStringHandling() {
        let score = WaterFeatureDetector.calculateWaterScore(description: "")
        XCTAssertEqual(score, 0.0, "Empty description should return 0.0")
    }

    func testComplexScenarios() {
        // Test realistic property descriptions
        let realExample1 = "2.5 AC WITH CREEK FRONTAGE AND POND ACCESS, BEAUTIFUL WATERFRONT VIEWS"
        let score1 = WaterFeatureDetector.calculateWaterScore(description: realExample1)
        // creek (3.0) + pond (3.0) + waterfront (1.0) = 7.0
        XCTAssertEqual(score1, 7.0, accuracy: 0.01, "Complex real example 1")

        let realExample2 = "BEAUTIFUL PROPERTY ON TRIBUTARY WITH WETLAND AREAS AND RIPARIAN BUFFER"
        let score2 = WaterFeatureDetector.calculateWaterScore(description: realExample2)
        // tributary (2.0) + wetland (2.0) + riparian (1.0) = 5.0
        XCTAssertEqual(score2, 5.0, accuracy: 0.01, "Complex real example 2")

        let realExample3 = "10 ACRES WITH STREAM, BRANCH, AND SPRING - MULTIPLE WATER SOURCES"
        let score3 = WaterFeatureDetector.calculateWaterScore(description: realExample3)
        // stream (3.0) + branch (2.0) + spring (3.0) + water (1.0) = 9.0
        XCTAssertEqual(score3, 9.0, accuracy: 0.01, "Complex real example 3")
    }

    func testWaterFeatureDetailsStructure() {
        let description = "Beautiful creek frontage with pond access"
        let details = WaterFeatureDetector.getWaterFeatureDetails(description: description)

        XCTAssertEqual(details.score, 6.0, accuracy: 0.01, "Score should match simple calculation")
        XCTAssertTrue(details.hasWaterFeatures, "Should detect water features")
        XCTAssertEqual(details.category, .primary, "Should be classified as primary")
        XCTAssertEqual(Set(details.features), Set(["Creek", "Pond"]), "Should detect both features")
    }

    func testWaterFeatureCategoryClassification() {
        let primaryExample = "Beautiful creek frontage"
        let primaryDetails = WaterFeatureDetector.getWaterFeatureDetails(description: primaryExample)
        XCTAssertEqual(primaryDetails.category, .primary, "Creek should be classified as primary")

        let secondaryExample = "Property near wetland"
        let secondaryDetails = WaterFeatureDetector.getWaterFeatureDetails(description: secondaryExample)
        XCTAssertEqual(secondaryDetails.category, .secondary, "Wetland should be classified as secondary")

        let tertiaryExample = "Waterfront location"
        let tertiaryDetails = WaterFeatureDetector.getWaterFeatureDetails(description: tertiaryExample)
        XCTAssertEqual(tertiaryDetails.category, .tertiary, "Waterfront should be classified as tertiary")

        let noWaterExample = "Dry mountain property"
        let noWaterDetails = WaterFeatureDetector.getWaterFeatureDetails(description: noWaterExample)
        XCTAssertEqual(noWaterDetails.category, .none, "No water features should be classified as none")
    }

    func testWaterFeatureCategoryWeights() {
        XCTAssertEqual(WaterFeatureCategory.none.weight, 0.0)
        XCTAssertEqual(WaterFeatureCategory.tertiary.weight, 1.0)
        XCTAssertEqual(WaterFeatureCategory.secondary.weight, 2.0)
        XCTAssertEqual(WaterFeatureCategory.primary.weight, 3.0)
    }

    func testDisplayText() {
        let withFeatures = WaterFeatureDetails(score: 5.0, features: ["Creek", "Pond"], category: .primary)
        XCTAssertEqual(withFeatures.displayText, "Creek, Pond")

        let noFeatures = WaterFeatureDetails(score: 0.0, features: [], category: .none)
        XCTAssertEqual(noFeatures.displayText, "No water features detected")
    }

    func testPartialWordMatching() {
        // Should NOT match partial words
        let descriptions = [
            "Screech owl habitat",  // "creek" is inside "screech"
            "Streaming video available",  // "stream" is inside "streaming"
            "Lakeshore drive address"  // Should match "shore" but not create false "lake"
        ]

        let score1 = WaterFeatureDetector.calculateWaterScore(description: descriptions[0])
        XCTAssertEqual(score1, 0.0, "Should not match 'creek' inside 'screech'")

        let score2 = WaterFeatureDetector.calculateWaterScore(description: descriptions[1])
        XCTAssertEqual(score2, 0.0, "Should not match 'stream' inside 'streaming'")

        let score3 = WaterFeatureDetector.calculateWaterScore(description: descriptions[2])
        XCTAssertEqual(score3, 1.0, "Should match 'shore' and score 1.0")
    }
}