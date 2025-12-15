import SwiftUI
import MapKit
import CoreLocation

struct MapView: View {
    @StateObject private var viewModel = MapViewModel()
    @State private var selectedProperty: Property?
    @State private var showingPropertyDetail = false

    var body: some View {
        NavigationView {
            ZStack {
                Map(coordinateRegion: $viewModel.region,
                    interactionModes: .all,
                    showsUserLocation: true,
                    annotationItems: viewModel.properties) { property in
                    MapAnnotation(coordinate: viewModel.coordinate(for: property)) {
                        PropertyMapPin(property: property) {
                            selectedProperty = property
                            showingPropertyDetail = true
                        }
                    }
                }
                .onAppear {
                    viewModel.loadProperties()
                    viewModel.requestLocationPermission()
                }

                VStack {
                    Spacer()

                    HStack {
                        Spacer()

                        VStack(spacing: 12) {
                            Button(action: viewModel.centerOnUserLocation) {
                                Image(systemName: "location")
                                    .font(.title2)
                                    .foregroundColor(.white)
                                    .frame(width: 44, height: 44)
                                    .background(Color.blue)
                                    .clipShape(Circle())
                                    .shadow(radius: 4)
                            }

                            Button(action: viewModel.centerOnAlabama) {
                                Image(systemName: "map")
                                    .font(.title2)
                                    .foregroundColor(.white)
                                    .frame(width: 44, height: 44)
                                    .background(Color.green)
                                    .clipShape(Circle())
                                    .shadow(radius: 4)
                            }
                        }
                        .padding(.trailing)
                    }
                    .padding(.bottom, 100)
                }
            }
            .navigationTitle("Property Map")
            .sheet(isPresented: $showingPropertyDetail) {
                if let property = selectedProperty {
                    PropertyDetailView(property: property)
                }
            }
        }
    }
}

struct PropertyMapPin: View {
    let property: Property
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                ZStack {
                    Circle()
                        .fill(pinColor)
                        .frame(width: 30, height: 30)
                        .shadow(radius: 2)

                    Text("\(Int(property.investmentScore))")
                        .font(.caption2.bold())
                        .foregroundColor(.white)
                }

                Text(property.county ?? "")
                    .font(.caption2)
                    .padding(.horizontal, 4)
                    .padding(.vertical, 2)
                    .background(Color.black.opacity(0.7))
                    .foregroundColor(.white)
                    .clipShape(Capsule())
            }
        }
    }

    private var pinColor: Color {
        switch property.investmentScore {
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

struct PropertyMapView: View {
    let property: Property
    @Environment(\.presentationMode) var presentationMode

    private var coordinate: CLLocationCoordinate2D {
        // In a real app, you'd geocode the property address
        // For now, return approximate Alabama center
        return CLLocationCoordinate2D(latitude: 32.806671, longitude: -86.791130)
    }

    var body: some View {
        NavigationView {
            Map(coordinateRegion: .constant(MKCoordinateRegion(
                center: coordinate,
                span: MKCoordinateSpan(latitudeDelta: 0.01, longitudeDelta: 0.01)
            )), annotationItems: [property]) { prop in
                MapAnnotation(coordinate: coordinate) {
                    PropertyMapPin(property: prop) {}
                }
            }
            .navigationTitle(property.parcelId ?? "Property Location")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        presentationMode.wrappedValue.dismiss()
                    }
                }

                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Directions") {
                        openInMaps()
                    }
                }
            }
        }
    }

    private func openInMaps() {
        let placemark = MKPlacemark(coordinate: coordinate)
        let mapItem = MKMapItem(placemark: placemark)
        mapItem.name = property.parcelId
        mapItem.openInMaps(launchOptions: [MKLaunchOptionsDirectionsModeKey: MKLaunchOptionsDirectionsModeDriving])
    }
}

#Preview {
    MapView()
}