import Foundation

struct InvestmentScoreWeights {
    static let pricePerAcre: Double = 0.4
    static let acreagePreference: Double = 0.3
    static let waterFeatures: Double = 0.2
    static let assessedValueRatio: Double = 0.1

    static var isValid: Bool {
        let sum = pricePerAcre + acreagePreference + waterFeatures + assessedValueRatio
        return abs(sum - 1.0) < 0.001
    }
}

struct InvestmentCalculator {

    static let preferredMinAcres: Double = 2.0
    static let preferredMaxAcres: Double = 4.0

    static func calculateInvestmentScore(
        pricePerAcre: Double,
        acreage: Double,
        waterScore: Double,
        assessedValueRatio: Double
    ) -> Double {

        guard InvestmentScoreWeights.isValid else {
            fatalError("Investment score weights must sum to 1.0")
        }

        var score: Double = 0.0

        // Price per acre score (lower is better, so invert)
        if pricePerAcre > 0 {
            let maxPriceScore = min(100, 10000 / pricePerAcre)
            score += maxPriceScore * InvestmentScoreWeights.pricePerAcre
        }

        // Acreage preference score (peak around 2-4 acres)
        if acreage > 0 {
            let acreageScore: Double
            if acreage >= preferredMinAcres && acreage <= preferredMaxAcres {
                acreageScore = 100
            } else if acreage < preferredMinAcres {
                acreageScore = max(0, 100 * acreage / preferredMinAcres)
            } else {
                let excess = acreage - preferredMaxAcres
                acreageScore = max(0, 100 - (excess * 10))
            }
            score += acreageScore * InvestmentScoreWeights.acreagePreference
        }

        // Water features score
        let waterNormalized = min(100, waterScore * 10)
        score += waterNormalized * InvestmentScoreWeights.waterFeatures

        // Assessed value ratio score (lower ratio is better - getting a bargain)
        if assessedValueRatio > 0 {
            let ratioScore = min(100, 100 / assessedValueRatio)
            score += ratioScore * InvestmentScoreWeights.assessedValueRatio
        }

        return (score * 10).rounded() / 10
    }

    static func calculateEstimatedAllInCost(
        bidAmount: Double,
        recordingFee: Double = 35.0,
        countyFeePercent: Double = 0.05,
        miscFees: Double = 100.0
    ) -> Double {

        guard bidAmount > 0 else { return 0.0 }

        let countyFee = bidAmount * countyFeePercent
        let totalCost = bidAmount + recordingFee + countyFee + miscFees

        return totalCost
    }

    static func calculatePricePerAcre(amount: Double, acreage: Double) -> Double {
        guard acreage > 0 else { return 0.0 }
        return amount / acreage
    }

    static func calculateAssessedValueRatio(bidAmount: Double, assessedValue: Double) -> Double {
        guard assessedValue > 0 else { return 0.0 }
        return bidAmount / assessedValue
    }
}