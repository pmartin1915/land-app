import SwiftUI

struct WaterFeatureAnalysisView: View {
    let property: Property

    private var waterFeatureDetails: WaterFeatureDetails {
        WaterFeatureDetector.getWaterFeatureDetails(description: property.propertyDescription ?? "")
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Score: \(property.waterScore, specifier: "%.1f")")
                    .font(.headline)
                    .fontWeight(.bold)

                Spacer()

                Text(waterFeatureDetails.category.rawValue)
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(categoryColor)
                    .foregroundColor(.white)
                    .clipShape(Capsule())
            }

            if waterFeatureDetails.hasWaterFeatures {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Detected Features:")
                        .font(.subheadline)
                        .fontWeight(.medium)

                    FlowLayout(items: waterFeatureDetails.features) { feature in
                        Text(feature)
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.blue.opacity(0.2))
                            .foregroundColor(.blue)
                            .clipShape(Capsule())
                    }
                }

                keywordBreakdown
            } else {
                Text("No water features detected in property description")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .italic()
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color(.systemGray4), lineWidth: 1)
        )
    }

    private var categoryColor: Color {
        switch waterFeatureDetails.category {
        case .none:
            return .gray
        case .tertiary:
            return .blue
        case .secondary:
            return .teal
        case .primary:
            return .cyan
        }
    }

    private var keywordBreakdown: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Keyword Analysis:")
                .font(.subheadline)
                .fontWeight(.medium)

            KeywordCategoryView(
                title: "Primary Keywords (3.0 points)",
                keywords: WaterFeatureKeywords.primary,
                description: property.propertyDescription ?? "",
                color: .green
            )

            KeywordCategoryView(
                title: "Secondary Keywords (2.0 points)",
                keywords: WaterFeatureKeywords.secondary,
                description: property.propertyDescription ?? "",
                color: .orange
            )

            KeywordCategoryView(
                title: "Tertiary Keywords (1.0 points)",
                keywords: WaterFeatureKeywords.tertiary,
                description: property.propertyDescription ?? "",
                color: .blue
            )
        }
    }
}

struct KeywordCategoryView: View {
    let title: String
    let keywords: [String]
    let description: String
    let color: Color

    private var matchedKeywords: [String] {
        let descriptionLower = description.lowercased()
        return keywords.filter { keyword in
            descriptionLower.contains(keyword.lowercased())
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(color)

            if matchedKeywords.isEmpty {
                Text("None found")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .italic()
            } else {
                FlowLayout(items: matchedKeywords) { keyword in
                    Text(keyword.capitalized)
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(color.opacity(0.2))
                        .foregroundColor(color)
                        .clipShape(Capsule())
                }
            }
        }
    }
}

struct FlowLayout<Item: Hashable, ItemView: View>: View {
    let items: [Item]
    let itemView: (Item) -> ItemView

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(Array(items.chunked(into: 3)), id: \.self) { chunk in
                HStack {
                    ForEach(chunk, id: \.self) { item in
                        itemView(item)
                    }
                    Spacer()
                }
            }
        }
    }
}

extension Array {
    func chunked(into size: Int) -> [[Element]] {
        return stride(from: 0, to: count, by: size).map {
            Array(self[$0..<Swift.min($0 + size, count)])
        }
    }
}

#Preview {
    let context = PersistenceController.preview.container.viewContext
    let property = Property(context: context)
    property.propertyDescription = "Beautiful 2.5 acre lot with creek frontage and pond access"
    property.waterScore = 6.0

    return WaterFeatureAnalysisView(property: property)
        .padding()
}