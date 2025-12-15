import SwiftUI

struct PropertyListView: View {
    @StateObject private var viewModel = PropertyListViewModel()
    @State private var showingFilters = false
    @State private var showingSortOptions = false

    var body: some View {
        NavigationView {
            VStack {
                if viewModel.isLoading {
                    ProgressView("Loading properties...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    propertyList
                }
            }
            .navigationTitle("Properties")
            .searchable(text: $viewModel.searchText, prompt: "Search properties...")
            .toolbar {
                ToolbarItemGroup(placement: .navigationBarTrailing) {
                    Button(action: { showingSortOptions = true }) {
                        Image(systemName: "arrow.up.arrow.down")
                    }

                    Button(action: { showingFilters = true }) {
                        Image(systemName: "line.3.horizontal.decrease.circle")
                    }

                    Button(action: { viewModel.refreshData() }) {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
            .sheet(isPresented: $showingFilters) {
                FilterView(filterOptions: viewModel.filterOptions)
            }
            .confirmationDialog("Sort Options", isPresented: $showingSortOptions) {
                ForEach(SortOption.allCases, id: \.self) { option in
                    Button(option.rawValue) {
                        viewModel.sortOption = option
                    }
                }
                Button("Cancel", role: .cancel) {}
            }
        }
    }

    private var propertyList: some View {
        List {
            if viewModel.filteredProperties.isEmpty {
                Text("No properties found")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
            } else {
                ForEach(viewModel.filteredProperties, id: \.objectID) { property in
                    NavigationLink(destination: PropertyDetailView(property: property)) {
                        PropertyRowView(property: property)
                    }
                }
            }
        }
        .refreshable {
            viewModel.refreshData()
        }
    }
}

struct PropertyRowView: View {
    let property: Property

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(property.parcelId ?? "Unknown ID")
                        .font(.headline)
                        .foregroundColor(.primary)

                    if let county = property.county {
                        Text(county)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Text(property.amount.formatted(.currency(code: "USD")))
                        .font(.headline)
                        .foregroundColor(.primary)

                    Text("\(property.acreage, specifier: "%.2f") acres")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }

            HStack {
                Label("\(property.pricePerAcre.formatted(.currency(code: "USD")))/acre", systemImage: "dollarsign.circle")
                    .font(.caption)
                    .foregroundColor(.secondary)

                Spacer()

                if property.waterScore > 0 {
                    Label("Water", systemImage: "drop.fill")
                        .font(.caption)
                        .foregroundColor(.blue)
                }

                InvestmentScoreBadge(score: property.investmentScore)
            }

            if let description = property.propertyDescription, !description.isEmpty {
                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }
}

struct InvestmentScoreBadge: View {
    let score: Double

    var body: some View {
        Text("\(score, specifier: "%.1f")")
            .font(.caption.bold())
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(scoreColor)
            .foregroundColor(.white)
            .clipShape(Capsule())
    }

    private var scoreColor: Color {
        switch score {
        case 80...:
            return .green
        case 60..<80:
            return .orange
        case 40..<60:
            return .yellow
        default:
            return .red
        }
    }
}

#Preview {
    PropertyListView()
        .environment(\.managedObjectContext, PersistenceController.preview.container.viewContext)
}