import Foundation

// Central coordinator for all device sources: BLE, USB, GPS.
// Provides a unified device inventory for the ChatViewModel's device context.

@MainActor
final class DeviceManager: ObservableObject {
    static let shared = DeviceManager()

    @Published var allDevicesSummary: [String: Any] = [:]

    private var refreshTimer: Timer?
    private let ble = BLEManager.shared
    private let gps = GPSManager.shared
    private let acc = AccessoryDetector.shared

    private init() {
        refresh()
        refreshTimer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
    }

    func refresh() {
        allDevicesSummary = buildSummary()
    }

    private func buildSummary() -> [String: Any] {
        var summary: [String: Any] = [:]

        summary["bluetooth"] = ble.deviceSummary
        summary["gps"]       = gps.currentLocationSummary()
        summary["usb_accessories"] = [
            "count":   acc.accessories.count,
            "devices": acc.accessorySummary,
        ]
        summary["timestamp"] = ISO8601DateFormatter().string(from: Date())

        return summary
    }

    func deviceContextString() -> String {
        var parts: [String] = []

        if let connected = ble.connectedDevice {
            parts.append("BLE:\(connected.displayName)(\(connected.rssi)dBm)")
        } else if !ble.discoveredDevices.isEmpty {
            parts.append("\(ble.discoveredDevices.count) BLE")
        }

        if let loc = gps.location {
            parts.append(String(format: "GPS:%.4f,%.4f", loc.coordinate.latitude, loc.coordinate.longitude))
        }

        if !acc.accessories.isEmpty {
            let names = acc.accessories.prefix(3).map { $0.name }.joined(separator: "/")
            parts.append("USB:\(names)")
        }

        return parts.isEmpty ? "iPhone (sin dispositivos)" : "iPhone | " + parts.joined(separator: " | ")
    }
}
