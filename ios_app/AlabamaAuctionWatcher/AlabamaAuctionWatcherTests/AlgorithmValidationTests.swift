import XCTest
@testable import AlabamaAuctionWatcher

final class AlgorithmValidationTests: XCTestCase {

    func testPythonSwiftAlgorithmConsistency() {
        // Test cases that should match exactly between Python and Swift implementations
        let testCases = [
            (pricePerAcre: 5000.0, acreage: 3.0, waterScore: 6.0, assessedValueRatio: 0.8, expectedScore: 52.8),
            (pricePerAcre: 2000.0, acreage: 2.5, waterScore: 3.0, assessedValueRatio: 0.6, expectedScore: 85.0),
            (pricePerAcre: 10000.0, acreage: 1.0, waterScore: 0.0, assessedValueRatio: 1.2, expectedScore: 23.3),
            (pricePerAcre: 3000.0, acreage: 4.0, waterScore: 9.0, assessedValueRatio: 0.5, expectedScore: 71.3)
        ]

        for (index, testCase) in testCases.enumerated() {
            let score = InvestmentCalculator.calculateInvestmentScore(
                pricePerAcre: testCase.pricePerAcre,
                acreage: testCase.acreage,
                waterScore: testCase.waterScore,
                assessedValueRatio: testCase.assessedValueRatio
            )

            XCTAssertEqual(
                score,
                testCase.expectedScore,
                accuracy: 0.5,
                "Test case \(index + 1) should match Python calculation within 0.5 points"
            )
        }
    }

    func testWaterScorePythonEquivalence() {
        // Test descriptions that should produce exact same scores as Python
        let testDescriptions = [
            ("Beautiful creek frontage", 3.0),
            ("Property with pond and stream", 6.0),
            ("Wetland area with tributary access", 4.0),
            ("Waterfront location with shore access", 2.0),
            ("Creek, branch, and spring on property", 8.0),
            ("No water features mentioned", 0.0),
            ("CREEK AND POND WITH WATER ACCESS", 7.0)
        ]

        for (description, expectedScore) in testDescriptions {
            let score = WaterFeatureDetector.calculateWaterScore(description: description)
            XCTAssertEqual(
                score,
                expectedScore,
                accuracy: 0.01,
                "Water score for '\(description)' should match Python exactly"
            )
        }
    }

    func testCountyValidationPythonEquivalence() {
        // Test county validation matches Python ALABAMA_COUNTY_CODES exactly
        let criticalCounties = [
            ("01", "Autauga"),
            ("02", "Mobile"),    // Corrected mapping
            ("05", "Baldwin"),   // Corrected mapping
            ("38", "Jefferson"),
            ("67", "Winston")
        ]

        for (code, expectedName) in criticalCounties {
            XCTAssertEqual(
                AlabamaCounties.codes[code],
                expectedName,
                "County code \(code) should map to \(expectedName) exactly as in Python"
            )

            XCTAssertEqual(
                try CountyValidator.getCountyCode(for: expectedName),
                code,
                "County name \(expectedName) should map to code \(code) exactly as in Python"
            )
        }
    }

    func testAllInCostCalculationPythonEquivalence() {
        // Test cost calculation matches Python calculate_estimated_all_in_cost exactly
        let testAmounts = [5000.0, 10000.0, 15000.0, 25000.0]
        let recordingFee = 35.0
        let countyFeePercent = 0.05
        let miscFees = 100.0

        for amount in testAmounts {
            let swiftResult = InvestmentCalculator.calculateEstimatedAllInCost(
                bidAmount: amount,
                recordingFee: recordingFee,
                countyFeePercent: countyFeePercent,
                miscFees: miscFees
            )

            // Python calculation: amount + 35 + (amount * 0.05) + 100
            let pythonResult = amount + recordingFee + (amount * countyFeePercent) + miscFees

            XCTAssertEqual(
                swiftResult,
                pythonResult,
                accuracy: 0.01,
                "All-in cost for $\(amount) should match Python calculation exactly"
            )
        }
    }

    func testEdgeCaseHandling() {
        // Test edge cases that Python handles
        XCTAssertEqual(
            InvestmentCalculator.calculateInvestmentScore(pricePerAcre: 0, acreage: 0, waterScore: 0, assessedValueRatio: 0),
            0.0,
            "Zero inputs should return zero score"
        )

        XCTAssertEqual(
            WaterFeatureDetector.calculateWaterScore(description: ""),
            0.0,
            "Empty description should return zero water score"
        )

        XCTAssertEqual(
            InvestmentCalculator.calculateEstimatedAllInCost(bidAmount: -100),
            0.0,
            "Negative bid amount should return zero cost"
        )

        XCTAssertFalse(
            CountyValidator.isValidCounty(code: "00"),
            "Invalid county code should return false"
        )
    }

    func testWeightSumValidation() {
        // Critical test: Investment score weights must sum to exactly 1.0
        let weights = [
            InvestmentScoreWeights.pricePerAcre,
            InvestmentScoreWeights.acreagePreference,
            InvestmentScoreWeights.waterFeatures,
            InvestmentScoreWeights.assessedValueRatio
        ]

        let sum = weights.reduce(0, +)
        XCTAssertEqual(sum, 1.0, accuracy: 0.001, "Investment score weights must sum to exactly 1.0")

        // Verify individual weights match Python INVESTMENT_SCORE_WEIGHTS
        XCTAssertEqual(InvestmentScoreWeights.pricePerAcre, 0.4, accuracy: 0.001)
        XCTAssertEqual(InvestmentScoreWeights.acreagePreference, 0.3, accuracy: 0.001)
        XCTAssertEqual(InvestmentScoreWeights.waterFeatures, 0.2, accuracy: 0.001)
        XCTAssertEqual(InvestmentScoreWeights.assessedValueRatio, 0.1, accuracy: 0.001)
    }

    func testKeywordArrayConsistency() {
        // Verify water keyword arrays match Python exactly
        let pythonPrimary = ["creek", "stream", "river", "lake", "pond", "spring"]
        let pythonSecondary = ["branch", "run", "brook", "tributary", "wetland", "marsh"]
        let pythonTertiary = ["water", "aquatic", "riparian", "shore", "bank", "waterfront"]

        XCTAssertEqual(WaterFeatureKeywords.primary.sorted(), pythonPrimary.sorted())
        XCTAssertEqual(WaterFeatureKeywords.secondary.sorted(), pythonSecondary.sorted())
        XCTAssertEqual(WaterFeatureKeywords.tertiary.sorted(), pythonTertiary.sorted())

        // Verify weights match Python WATER_SCORE_WEIGHTS
        XCTAssertEqual(WaterFeatureKeywords.weights.primary, 3.0)
        XCTAssertEqual(WaterFeatureKeywords.weights.secondary, 2.0)
        XCTAssertEqual(WaterFeatureKeywords.weights.tertiary, 1.0)
    }

    func testCountyCountConsistency() {
        // Alabama has exactly 67 counties
        XCTAssertEqual(AlabamaCounties.totalCount, 67, "Alabama must have exactly 67 counties")
        XCTAssertEqual(AlabamaCounties.codes.count, 67, "County codes dictionary must have 67 entries")
        XCTAssertEqual(Set(AlabamaCounties.codes.values).count, 67, "All county names must be unique")

        // Verify code range is 01-67
        for code in AlabamaCounties.codes.keys {
            guard let intCode = Int(code) else {
                XCTFail("County code \(code) should be convertible to integer")
                continue
            }
            XCTAssertTrue(intCode >= 1 && intCode <= 67, "County code \(code) should be in range 01-67")
        }
    }

    func testRealWorldScenarios() {
        // Test with realistic property data that would come from Alabama ADOR
        let realProperty1 = (
            description: "2.5 AC WITH CREEK FRONTAGE",
            amount: 8500.0,
            acreage: 2.5,
            assessedValue: 15000.0
        )

        let pricePerAcre1 = realProperty1.amount / realProperty1.acreage
        let waterScore1 = WaterFeatureDetector.calculateWaterScore(description: realProperty1.description)
        let ratio1 = realProperty1.amount / realProperty1.assessedValue
        let score1 = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: pricePerAcre1,
            acreage: realProperty1.acreage,
            waterScore: waterScore1,
            assessedValueRatio: ratio1
        )

        XCTAssertGreaterThan(score1, 50.0, "Good property with water should score above 50")
        XCTAssertEqual(waterScore1, 3.0, "Creek should give 3.0 water score")

        let realProperty2 = (
            description: "10 ACRES TIMBER LAND",
            amount: 12000.0,
            acreage: 10.0,
            assessedValue: 8000.0
        )

        let pricePerAcre2 = realProperty2.amount / realProperty2.acreage
        let waterScore2 = WaterFeatureDetector.calculateWaterScore(description: realProperty2.description)
        let ratio2 = realProperty2.amount / realProperty2.assessedValue
        let score2 = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: pricePerAcre2,
            acreage: realProperty2.acreage,
            waterScore: waterScore2,
            assessedValueRatio: ratio2
        )

        XCTAssertEqual(waterScore2, 0.0, "No water keywords should give 0 water score")
        XCTAssertLessThan(score2, score1, "Property without water should score lower than one with water")
    }

    func testPerformanceRequirements() {
        // Test that algorithms perform within reasonable time limits
        let startTime = CFAbsoluteTimeGetCurrent()

        for _ in 0..<1000 {
            _ = InvestmentCalculator.calculateInvestmentScore(
                pricePerAcre: 5000.0,
                acreage: 3.0,
                waterScore: 6.0,
                assessedValueRatio: 0.8
            )
        }

        let timeElapsed = CFAbsoluteTimeGetCurrent() - startTime
        XCTAssertLessThan(timeElapsed, 1.0, "1000 investment calculations should complete in under 1 second")

        let waterStartTime = CFAbsoluteTimeGetCurrent()

        for _ in 0..<1000 {
            _ = WaterFeatureDetector.calculateWaterScore(description: "Beautiful creek frontage with pond access")
        }

        let waterTimeElapsed = CFAbsoluteTimeGetCurrent() - waterStartTime
        XCTAssertLessThan(waterTimeElapsed, 1.0, "1000 water score calculations should complete in under 1 second")
    }
}