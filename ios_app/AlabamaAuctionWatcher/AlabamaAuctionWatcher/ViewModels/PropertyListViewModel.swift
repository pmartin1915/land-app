import Foundation
import CoreData
import Combine

@MainActor
class PropertyListViewModel: ObservableObject {
    @Published var properties: [Property] = []
    @Published var filteredProperties: [Property] = []
    @Published var isLoading = false
    @Published var searchText = ""
    @Published var sortOption: SortOption = .investmentScoreDescending
    @Published var filterOptions = FilterOptions()

    private var cancellables = Set<AnyCancellable>()
    private let persistenceController: PersistenceController

    init(persistenceController: PersistenceController = .shared) {
        self.persistenceController = persistenceController
        setupSubscriptions()
        loadProperties()
    }

    private func setupSubscriptions() {
        $searchText
            .debounce(for: .milliseconds(300), scheduler: RunLoop.main)
            .sink { _ in
                self.applyFiltersAndSort()
            }
            .store(in: &cancellables)

        $sortOption
            .sink { _ in
                self.applyFiltersAndSort()
            }
            .store(in: &cancellables)

        filterOptions.objectWillChange
            .sink { _ in
                self.applyFiltersAndSort()
            }
            .store(in: &cancellables)
    }

    func loadProperties() {
        isLoading = true

        let context = persistenceController.container.viewContext
        let request: NSFetchRequest<Property> = Property.fetchRequest()
        request.sortDescriptors = [NSSortDescriptor(keyPath: \Property.investmentScore, ascending: false)]

        do {
            properties = try context.fetch(request)
            applyFiltersAndSort()
        } catch {
            print("Error fetching properties: \(error)")
        }

        isLoading = false
    }

    private func applyFiltersAndSort() {
        var filtered = properties

        // Apply search filter
        if !searchText.isEmpty {
            filtered = filtered.filter { property in
                let searchLower = searchText.lowercased()
                return property.parcelId?.lowercased().contains(searchLower) ?? false ||
                       property.propertyDescription?.lowercased().contains(searchLower) ?? false ||
                       property.county?.lowercased().contains(searchLower) ?? false
            }
        }

        // Apply price filter
        if filterOptions.priceRange.lowerBound > 0 || filterOptions.priceRange.upperBound < Double.greatestFiniteMagnitude {
            filtered = filtered.filter { property in
                let price = property.amount
                return price >= filterOptions.priceRange.lowerBound && price <= filterOptions.priceRange.upperBound
            }
        }

        // Apply acreage filter
        if filterOptions.acreageRange.lowerBound > 0 || filterOptions.acreageRange.upperBound < Double.greatestFiniteMagnitude {
            filtered = filtered.filter { property in
                let acreage = property.acreage
                return acreage >= filterOptions.acreageRange.lowerBound && acreage <= filterOptions.acreageRange.upperBound
            }
        }

        // Apply water features filter
        if filterOptions.waterFeaturesOnly {
            filtered = filtered.filter { $0.waterScore > 0 }
        }

        // Apply county filter
        if let selectedCounty = filterOptions.selectedCounty, selectedCounty != "All" {
            filtered = filtered.filter { $0.county == selectedCounty }
        }

        // Apply investment score filter
        if filterOptions.minimumInvestmentScore > 0 {
            filtered = filtered.filter { $0.investmentScore >= filterOptions.minimumInvestmentScore }
        }

        // Apply sorting
        filtered = sortProperties(filtered)

        filteredProperties = filtered
    }

    private func sortProperties(_ properties: [Property]) -> [Property] {
        switch sortOption {
        case .investmentScoreDescending:
            return properties.sorted { $0.investmentScore > $1.investmentScore }
        case .investmentScoreAscending:
            return properties.sorted { $0.investmentScore < $1.investmentScore }
        case .priceAscending:
            return properties.sorted { $0.amount < $1.amount }
        case .priceDescending:
            return properties.sorted { $0.amount > $1.amount }
        case .pricePerAcreAscending:
            return properties.sorted { $0.pricePerAcre < $1.pricePerAcre }
        case .pricePerAcreDescending:
            return properties.sorted { $0.pricePerAcre > $1.pricePerAcre }
        case .acreageAscending:
            return properties.sorted { $0.acreage < $1.acreage }
        case .acreageDescending:
            return properties.sorted { $0.acreage > $1.acreage }
        case .waterScoreDescending:
            return properties.sorted { $0.waterScore > $1.waterScore }
        }
    }

    func refreshData() {
        loadProperties()
    }

    func calculateMetrics(for property: Property) {
        let waterScore = WaterFeatureDetector.calculateWaterScore(description: property.propertyDescription ?? "")
        let pricePerAcre = InvestmentCalculator.calculatePricePerAcre(amount: property.amount, acreage: property.acreage)
        let assessedValueRatio = InvestmentCalculator.calculateAssessedValueRatio(bidAmount: property.amount, assessedValue: property.assessedValue)
        let investmentScore = InvestmentCalculator.calculateInvestmentScore(
            pricePerAcre: pricePerAcre,
            acreage: property.acreage,
            waterScore: waterScore,
            assessedValueRatio: assessedValueRatio
        )
        let allInCost = InvestmentCalculator.calculateEstimatedAllInCost(bidAmount: property.amount)

        property.waterScore = waterScore
        property.pricePerAcre = pricePerAcre
        property.assessedValueRatio = assessedValueRatio
        property.investmentScore = investmentScore
        property.estimatedAllInCost = allInCost

        persistenceController.save()
    }
}

enum SortOption: String, CaseIterable {
    case investmentScoreDescending = "Investment Score (High to Low)"
    case investmentScoreAscending = "Investment Score (Low to High)"
    case priceAscending = "Price (Low to High)"
    case priceDescending = "Price (High to Low)"
    case pricePerAcreAscending = "Price/Acre (Low to High)"
    case pricePerAcreDescending = "Price/Acre (High to Low)"
    case acreageAscending = "Acreage (Low to High)"
    case acreageDescending = "Acreage (High to Low)"
    case waterScoreDescending = "Water Score (High to Low)"
}

class FilterOptions: ObservableObject {
    @Published var priceRange: ClosedRange<Double> = 0...50000
    @Published var acreageRange: ClosedRange<Double> = 0...10
    @Published var waterFeaturesOnly = false
    @Published var selectedCounty: String? = "All"
    @Published var minimumInvestmentScore: Double = 0

    static let allCounties = ["All"] + AlabamaCounties.allCounties.map(\.name)
}