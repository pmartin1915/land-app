import Foundation

struct WaterFeatureKeywords {

    static let primary = ["creek", "stream", "river", "lake", "pond", "spring"]

    static let secondary = ["branch", "run", "brook", "tributary", "wetland", "marsh"]

    static let tertiary = ["water", "aquatic", "riparian", "shore", "bank", "waterfront"]

    static let weights: (primary: Double, secondary: Double, tertiary: Double) = (3.0, 2.0, 1.0)
}

struct WaterFeatureDetector {

    static func calculateWaterScore(description: String) -> Double {

        guard !description.isEmpty else { return 0.0 }

        let descriptionLower = description.lowercased()
        var score: Double = 0.0

        // Check primary keywords
        for keyword in WaterFeatureKeywords.primary {
            if descriptionLower.contains(keyword.lowercased()) {
                score += WaterFeatureKeywords.weights.primary
            }
        }

        // Check secondary keywords
        for keyword in WaterFeatureKeywords.secondary {
            if descriptionLower.contains(keyword.lowercased()) {
                score += WaterFeatureKeywords.weights.secondary
            }
        }

        // Check tertiary keywords
        for keyword in WaterFeatureKeywords.tertiary {
            if descriptionLower.contains(keyword.lowercased()) {
                score += WaterFeatureKeywords.weights.tertiary
            }
        }

        return score
    }

    static func getWaterFeatureDetails(description: String) -> WaterFeatureDetails {
        guard !description.isEmpty else {
            return WaterFeatureDetails(score: 0.0, features: [], category: .none)
        }

        let descriptionLower = description.lowercased()
        var foundFeatures: [String] = []
        var totalScore: Double = 0.0
        var highestCategory: WaterFeatureCategory = .none

        // Check primary keywords
        for keyword in WaterFeatureKeywords.primary {
            if descriptionLower.contains(keyword.lowercased()) {
                foundFeatures.append(keyword.capitalized)
                totalScore += WaterFeatureKeywords.weights.primary
                highestCategory = .primary
            }
        }

        // Check secondary keywords
        for keyword in WaterFeatureKeywords.secondary {
            if descriptionLower.contains(keyword.lowercased()) {
                foundFeatures.append(keyword.capitalized)
                totalScore += WaterFeatureKeywords.weights.secondary
                if highestCategory == .none {
                    highestCategory = .secondary
                }
            }
        }

        // Check tertiary keywords
        for keyword in WaterFeatureKeywords.tertiary {
            if descriptionLower.contains(keyword.lowercased()) {
                foundFeatures.append(keyword.capitalized)
                totalScore += WaterFeatureKeywords.weights.tertiary
                if highestCategory == .none {
                    highestCategory = .tertiary
                }
            }
        }

        return WaterFeatureDetails(
            score: totalScore,
            features: Array(Set(foundFeatures)).sorted(),
            category: highestCategory
        )
    }
}

enum WaterFeatureCategory: String, CaseIterable {
    case none = "No Water Features"
    case tertiary = "Minor Water Features"
    case secondary = "Moderate Water Features"
    case primary = "Major Water Features"

    var color: String {
        switch self {
        case .none: return "gray"
        case .tertiary: return "blue"
        case .secondary: return "teal"
        case .primary: return "cyan"
        }
    }

    var weight: Double {
        switch self {
        case .none: return 0.0
        case .tertiary: return WaterFeatureKeywords.weights.tertiary
        case .secondary: return WaterFeatureKeywords.weights.secondary
        case .primary: return WaterFeatureKeywords.weights.primary
        }
    }
}

struct WaterFeatureDetails {
    let score: Double
    let features: [String]
    let category: WaterFeatureCategory

    var hasWaterFeatures: Bool {
        return score > 0
    }

    var displayText: String {
        if features.isEmpty {
            return "No water features detected"
        } else {
            return features.joined(separator: ", ")
        }
    }
}