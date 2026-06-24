import Foundation
import CoreLocation
import Combine

@MainActor
final class GPSManager: NSObject, ObservableObject {
    static let shared = GPSManager()

    @Published var authorizationStatus: CLAuthorizationStatus = .notDetermined
    @Published var location: CLLocation?
    @Published var address: String?
    @Published var isTracking = false
    @Published var lastError: String?

    private let manager = CLLocationManager()
    private let geocoder = CLGeocoder()

    override private init() {
        super.init()
        manager.delegate        = self
        manager.desiredAccuracy = kCLLocationAccuracyBest
    }

    func requestPermission() {
        manager.requestWhenInUseAuthorization()
    }

    func startTracking() {
        guard authorizationStatus == .authorizedWhenInUse || authorizationStatus == .authorizedAlways else {
            requestPermission()
            return
        }
        isTracking = true
        manager.startUpdatingLocation()
    }

    func stopTracking() {
        isTracking = false
        manager.stopUpdatingLocation()
    }

    func currentLocationSummary() -> [String: Any] {
        guard let loc = location else {
            return ["available": false, "error": lastError ?? "Sin permiso GPS"]
        }
        return [
            "available":  true,
            "latitude":   loc.coordinate.latitude,
            "longitude":  loc.coordinate.longitude,
            "altitude_m": loc.altitude,
            "accuracy_m": loc.horizontalAccuracy,
            "address":    address ?? "desconocida",
            "timestamp":  ISO8601DateFormatter().string(from: loc.timestamp),
        ]
    }

    private func reverseGeocode(_ location: CLLocation) {
        geocoder.reverseGeocodeLocation(location) { [weak self] placemarks, _ in
            guard let place = placemarks?.first else { return }
            Task { @MainActor in
                var parts: [String] = []
                if let street = place.thoroughfare  { parts.append(street) }
                if let city   = place.locality      { parts.append(city) }
                if let country = place.country      { parts.append(country) }
                self?.address = parts.joined(separator: ", ")
            }
        }
    }
}

extension GPSManager: CLLocationManagerDelegate {
    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        Task { @MainActor in self.authorizationStatus = manager.authorizationStatus }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else { return }
        Task { @MainActor in
            self.location = loc
            self.reverseGeocode(loc)
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        Task { @MainActor in self.lastError = error.localizedDescription }
    }
}
