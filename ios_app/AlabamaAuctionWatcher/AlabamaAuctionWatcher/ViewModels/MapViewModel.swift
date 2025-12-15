import Foundation
import MapKit
import CoreLocation
import CoreData

@MainActor
class MapViewModel: NSObject, ObservableObject {
    @Published var region = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 32.806671, longitude: -86.791130),
        span: MKCoordinateSpan(latitudeDelta: 5.0, longitudeDelta: 5.0)
    )
    @Published var properties: [Property] = []
    @Published var userLocation: CLLocationCoordinate2D?

    private let locationManager = CLLocationManager()
    private let persistenceController: PersistenceController

    init(persistenceController: PersistenceController = .shared) {
        self.persistenceController = persistenceController
        super.init()
        setupLocationManager()
    }

    private func setupLocationManager() {
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyBest
    }

    func requestLocationPermission() {
        switch locationManager.authorizationStatus {
        case .notDetermined:
            locationManager.requestWhenInUseAuthorization()
        case .denied, .restricted:
            break
        case .authorizedWhenInUse, .authorizedAlways:
            locationManager.startUpdatingLocation()
        @unknown default:
            break
        }
    }

    func loadProperties() {
        let context = persistenceController.container.viewContext
        let request: NSFetchRequest<Property> = Property.fetchRequest()
        request.predicate = NSPredicate(format: "investmentScore > 0")
        request.sortDescriptors = [NSSortDescriptor(keyPath: \Property.investmentScore, ascending: false)]

        do {
            properties = try context.fetch(request)
        } catch {
            print("Error fetching properties: \(error)")
        }
    }

    func coordinate(for property: Property) -> CLLocationCoordinate2D {
        // In a real app, you would:
        // 1. Geocode the property address
        // 2. Store lat/lng in Core Data
        // 3. Use stored coordinates

        // For demo purposes, return approximate locations in Alabama
        let baseLatitude = 32.806671
        let baseLongitude = -86.791130

        // Generate pseudo-random coordinates based on parcel ID
        let parcelHash = property.parcelId?.hashValue ?? 0
        let latOffset = Double(parcelHash % 1000) / 10000.0 - 0.05
        let lngOffset = Double((parcelHash / 1000) % 1000) / 10000.0 - 0.05

        return CLLocationCoordinate2D(
            latitude: baseLatitude + latOffset,
            longitude: baseLongitude + lngOffset
        )
    }

    func centerOnUserLocation() {
        guard let userLocation = userLocation else {
            requestLocationPermission()
            return
        }

        withAnimation {
            region = MKCoordinateRegion(
                center: userLocation,
                span: MKCoordinateSpan(latitudeDelta: 0.1, longitudeDelta: 0.1)
            )
        }
    }

    func centerOnAlabama() {
        withAnimation {
            region = MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: 32.806671, longitude: -86.791130),
                span: MKCoordinateSpan(latitudeDelta: 5.0, longitudeDelta: 5.0)
            )
        }
    }

    func centerOnProperty(_ property: Property) {
        let coordinate = self.coordinate(for: property)
        withAnimation {
            region = MKCoordinateRegion(
                center: coordinate,
                span: MKCoordinateSpan(latitudeDelta: 0.01, longitudeDelta: 0.01)
            )
        }
    }

    func findNearbyProperties(to location: CLLocationCoordinate2D, within radius: Double = 10000) -> [Property] {
        return properties.filter { property in
            let propertyLocation = coordinate(for: property)
            let distance = CLLocation(latitude: location.latitude, longitude: location.longitude)
                .distance(from: CLLocation(latitude: propertyLocation.latitude, longitude: propertyLocation.longitude))
            return distance <= radius
        }
    }
}

extension MapViewModel: CLLocationManagerDelegate {
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }

        DispatchQueue.main.async {
            self.userLocation = location.coordinate

            // Center on user location the first time
            if self.region.center.latitude == 32.806671 && self.region.center.longitude == -86.791130 {
                self.centerOnUserLocation()
            }
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("Location manager failed with error: \(error)")
    }

    func locationManager(_ manager: CLLocationManager, didChangeAuthorization status: CLAuthorizationStatus) {
        switch status {
        case .authorizedWhenInUse, .authorizedAlways:
            locationManager.startUpdatingLocation()
        case .denied, .restricted:
            print("Location access denied")
        case .notDetermined:
            break
        @unknown default:
            break
        }
    }
}