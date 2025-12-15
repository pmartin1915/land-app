import SwiftUI
import MapKit

struct PropertyDetailView: View {
    let property: Property
    @State private var showingPhotoCapture = false
    @State private var showingMap = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                headerSection

                investmentMetricsSection

                propertyDetailsSection

                waterFeaturesSection

                actionButtonsSection

                photosSection
            }
            .padding()
        }
        .navigationTitle("Property Details")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showingPhotoCapture) {
            PhotoCaptureView(property: property)
        }
        .sheet(isPresented: $showingMap) {
            PropertyMapView(property: property)
        }
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(property.parcelId ?? "Unknown ID")
                    .font(.title2.bold())

                Spacer()

                InvestmentScoreBadge(score: property.investmentScore)
            }

            if let county = property.county {
                Label(county + " County", systemImage: "location")
                    .foregroundColor(.secondary)
            }

            if let description = property.propertyDescription, !description.isEmpty {
                Text(description)
                    .font(.body)
                    .foregroundColor(.primary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }

    private var investmentMetricsSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Investment Analysis")
                .font(.title3.bold())

            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 2), spacing: 16) {
                MetricCard(
                    title: "Bid Amount",
                    value: property.amount.formatted(.currency(code: "USD")),
                    icon: "dollarsign.circle"
                )

                MetricCard(
                    title: "All-in Cost",
                    value: property.estimatedAllInCost.formatted(.currency(code: "USD")),
                    icon: "creditcard"
                )

                MetricCard(
                    title: "Acreage",
                    value: String(format: "%.2f acres", property.acreage),
                    icon: "map"
                )

                MetricCard(
                    title: "Price/Acre",
                    value: property.pricePerAcre.formatted(.currency(code: "USD")),
                    icon: "chart.line.uptrend.xyaxis"
                )
            }

            InvestmentBreakdownView(property: property)
        }
    }

    private var propertyDetailsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Property Details")
                .font(.title3.bold())

            VStack(spacing: 8) {
                if let assessedValue = property.assessedValue, assessedValue > 0 {
                    DetailRow(label: "Assessed Value", value: assessedValue.formatted(.currency(code: "USD")))
                }

                if let owner = property.ownerName, !owner.isEmpty {
                    DetailRow(label: "Owner", value: owner)
                }

                if let year = property.yearSold, !year.isEmpty {
                    DetailRow(label: "Year Sold", value: year)
                }

                if property.assessedValueRatio > 0 {
                    DetailRow(label: "Bid/Assessed Ratio", value: String(format: "%.2f", property.assessedValueRatio))
                }
            }
        }
    }

    private var waterFeaturesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Water Features")
                .font(.title3.bold())

            WaterFeatureAnalysisView(property: property)
        }
    }

    private var actionButtonsSection: some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                Button(action: { showingMap = true }) {
                    Label("View on Map", systemImage: "map")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Button(action: { showingPhotoCapture = true }) {
                    Label("Add Photos", systemImage: "camera")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }

            Button(action: {}) {
                Label("Get Directions", systemImage: "location.north")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
        }
    }

    private var photosSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Field Photos")
                .font(.title3.bold())

            if let photos = property.photos?.allObjects as? [PropertyPhoto], !photos.isEmpty {
                PhotoGridView(photos: photos)
            } else {
                Text("No photos yet. Take some field verification photos!")
                    .foregroundColor(.secondary)
                    .italic()
            }
        }
    }
}

struct MetricCard: View {
    let title: String
    let value: String
    let icon: String

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.blue)

            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)

            Text(value)
                .font(.headline)
                .fontWeight(.semibold)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.systemBackground))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color(.systemGray4), lineWidth: 1)
        )
    }
}

struct DetailRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.medium)
        }
    }
}

struct InvestmentBreakdownView: View {
    let property: Property

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Score Breakdown")
                .font(.subheadline.bold())

            let priceScore = calculatePriceScore()
            let acreageScore = calculateAcreageScore()
            let waterScore = min(100, property.waterScore * 10)
            let ratioScore = calculateRatioScore()

            ScoreBreakdownRow(
                label: "Price/Acre (40%)",
                score: priceScore,
                weight: 0.4
            )

            ScoreBreakdownRow(
                label: "Acreage Preference (30%)",
                score: acreageScore,
                weight: 0.3
            )

            ScoreBreakdownRow(
                label: "Water Features (20%)",
                score: waterScore,
                weight: 0.2
            )

            ScoreBreakdownRow(
                label: "Value Ratio (10%)",
                score: ratioScore,
                weight: 0.1
            )
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(8)
    }

    private func calculatePriceScore() -> Double {
        return property.pricePerAcre > 0 ? min(100, 10000 / property.pricePerAcre) : 0
    }

    private func calculateAcreageScore() -> Double {
        let acreage = property.acreage
        if acreage >= 2.0 && acreage <= 4.0 {
            return 100
        } else if acreage < 2.0 {
            return max(0, 100 * acreage / 2.0)
        } else {
            let excess = acreage - 4.0
            return max(0, 100 - (excess * 10))
        }
    }

    private func calculateRatioScore() -> Double {
        return property.assessedValueRatio > 0 ? min(100, 100 / property.assessedValueRatio) : 0
    }
}

struct ScoreBreakdownRow: View {
    let label: String
    let score: Double
    let weight: Double

    var body: some View {
        HStack {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)

            Spacer()

            Text("\(score, specifier: "%.1f")")
                .font(.caption)
                .fontWeight(.medium)

            Text("→")
                .font(.caption)
                .foregroundColor(.secondary)

            Text("\(score * weight, specifier: "%.1f")")
                .font(.caption)
                .fontWeight(.bold)
        }
    }
}

#Preview {
    NavigationView {
        PropertyDetailView(property: PersistenceController.preview.container.viewContext.registeredObjects.first(where: { $0 is Property }) as! Property)
    }
}