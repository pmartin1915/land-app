import XCTest
@testable import AlabamaAuctionWatcher

final class InvestmentCalculatorTests: XCTestCase {

    func testInvestmentScoreWeightsValidation() {
        XCTAssertTrue(InvestmentScoreWeights.isValid, "Investment score weights must sum to 1.0")

        let expectedSum = 1.0
        let actualSum = InvestmentScoreWeights.pricePerAcre +
                       InvestmentScoreWeights.acreagePreference +
                       InvestmentScoreWeights.waterFeatures +
                       InvestmentScoreWeights.assessedValueRatio

        XCTAssertEqual(actualSum, expectedSum, accuracy: 0.001, "Weights must sum to exactly 1.0")
    }

    func testInvestmentScoreCalculation() {
        // Test case matching Python implementation
        let pricePerAcre = 5000.0
        let acreage = 3.0
        let waterScore = 6.0
        let assessedValueRatio = 0.8

        let score = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: pricePerAcre,
            acreage: acreage,
            waterScore: waterScore,
            assessedValueRatio: assessedValueRatio
        )

        // Expected calculation:
        // Price score: min(100, 10000/5000) * 0.4 = 2.0 * 0.4 = 0.8
        // Acreage score: 100 * 0.3 = 30.0 (3.0 is in preferred range 2-4)
        // Water score: min(100, 6.0 * 10) * 0.2 = 60.0 * 0.2 = 12.0
        // Ratio score: min(100, 100/0.8) * 0.1 = 100.0 * 0.1 = 10.0
        // Total: 0.8 + 30.0 + 12.0 + 10.0 = 52.8

        XCTAssertEqual(score, 52.8, accuracy: 0.1, "Investment score calculation should match Python implementation")
    }

    func testPricePerAcreComponent() {
        // Test low price per acre (good score)
        let lowPriceScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: 1000.0,
            acreage: 3.0,
            waterScore: 0.0,
            assessedValueRatio: 1.0
        )

        // Test high price per acre (poor score)
        let highPriceScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: 20000.0,
            acreage: 3.0,
            waterScore: 0.0,
            assessedValueRatio: 1.0
        )

        XCTAssertGreaterThan(lowPriceScore, highPriceScore, "Lower price per acre should result in higher investment score")
    }

    func testAcreagePreferenceComponent() {
        // Test preferred acreage (2-4 acres)
        let preferredScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: 5000.0,
            acreage: 3.0,
            waterScore: 0.0,
            assessedValueRatio: 1.0
        )

        // Test too small acreage
        let tooSmallScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: 5000.0,
            acreage: 0.5,
            waterScore: 0.0,
            assessedValueRatio: 1.0
        )

        // Test too large acreage
        let tooLargeScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: 5000.0,
            acreage: 10.0,
            waterScore: 0.0,
            assessedValueRatio: 1.0
        )

        XCTAssertGreaterThan(preferredScore, tooSmallScore, "Preferred acreage should score higher than too small")
        XCTAssertGreaterThan(preferredScore, tooLargeScore, "Preferred acreage should score higher than too large")
    }

    func testWaterFeaturesComponent() {
        // Test with water features
        let withWaterScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: 5000.0,
            acreage: 3.0,
            waterScore: 6.0,
            assessedValueRatio: 1.0
        )

        // Test without water features
        let withoutWaterScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: 5000.0,
            acreage: 3.0,
            waterScore: 0.0,
            assessedValueRatio: 1.0
        )

        XCTAssertGreaterThan(withWaterScore, withoutWaterScore, "Properties with water features should score higher")
    }

    func testEstimatedAllInCost() {
        let bidAmount = 10000.0
        let allInCost = InvestmentCalculator.calculateEstimatedAllInCost(bidAmount: bidAmount)

        // Expected: 10000 + 35 (recording) + 500 (5% county) + 100 (misc) = 10635
        let expected = 10635.0
        XCTAssertEqual(allInCost, expected, accuracy: 0.01, "All-in cost calculation should match Python implementation")
    }

    func testEstimatedAllInCostWithCustomFees() {
        let bidAmount = 15000.0
        let recordingFee = 40.0
        let countyFeePercent = 0.06
        let miscFees = 150.0

        let allInCost = InvestmentCalculator.calculateEstimatedAllInCost(
            bidAmount: bidAmount,
            recordingFee: recordingFee,
            countyFeePercent: countyFeePercent,
            miscFees: miscFees
        )

        // Expected: 15000 + 40 + 900 (6%) + 150 = 16090
        let expected = 16090.0
        XCTAssertEqual(allInCost, expected, accuracy: 0.01, "Custom fee calculation should be accurate")
    }

    func testPricePerAcreCalculation() {
        let amount = 12000.0
        let acreage = 2.5
        let pricePerAcre = InvestmentCalculator.calculatePricePerAcre(amount: amount, acreage: acreage)

        let expected = 4800.0
        XCTAssertEqual(pricePerAcre, expected, accuracy: 0.01, "Price per acre should be amount divided by acreage")
    }

    func testPricePerAcreWithZeroAcreage() {
        let pricePerAcre = InvestmentCalculator.calculatePricePerAcre(amount: 10000.0, acreage: 0.0)
        XCTAssertEqual(pricePerAcre, 0.0, "Price per acre should be 0 when acreage is 0")
    }

    func testAssessedValueRatio() {
        let bidAmount = 8000.0
        let assessedValue = 12000.0
        let ratio = InvestmentCalculator.calculateAssessedValueRatio(bidAmount: bidAmount, assessedValue: assessedValue)

        let expected = 8000.0 / 12000.0
        XCTAssertEqual(ratio, expected, accuracy: 0.001, "Assessed value ratio should be bid amount divided by assessed value")
    }

    func testAssessedValueRatioWithZeroAssessed() {
        let ratio = InvestmentCalculator.calculateAssessedValueRatio(bidAmount: 10000.0, assessedValue: 0.0)
        XCTAssertEqual(ratio, 0.0, "Ratio should be 0 when assessed value is 0")
    }

    func testZeroInputHandling() {
        let score = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: 0.0,
            acreage: 0.0,
            waterScore: 0.0,
            assessedValueRatio: 0.0
        )

        XCTAssertEqual(score, 0.0, "Score should be 0 when all inputs are 0")
    }

    func testNegativeInputHandling() {
        let allInCost = InvestmentCalculator.calculateEstimatedAllInCost(bidAmount: -1000.0)
        XCTAssertEqual(allInCost, 0.0, "All-in cost should be 0 for negative bid amounts")
    }
}