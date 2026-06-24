import Foundation
import ExternalAccessory

struct DetectedAccessory: Identifiable {
    let id: UUID
    let name: String
    let manufacturer: String
    let modelNumber: String
    let serialNumber: String
    let protocolStrings: [String]
    let firmwareRevision: String

    init(from acc: EAAccessory) {
        id               = UUID()
        name             = acc.name
        manufacturer     = acc.manufacturer
        modelNumber      = acc.modelNumber
        serialNumber     = acc.serialNumber
        protocolStrings  = acc.protocolStrings
        firmwareRevision = acc.firmwareRevision
    }

    var summary: [String: Any] {
        [
            "name":        name,
            "manufacturer": manufacturer,
            "model":       modelNumber,
            "protocols":   protocolStrings,
            "firmware":    firmwareRevision,
        ]
    }
}

@MainActor
final class AccessoryDetector: ObservableObject {
    static let shared = AccessoryDetector()

    @Published var accessories: [DetectedAccessory] = []

    private init() {
        refreshAccessories()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(accessoryDidConnect),
            name: .EAAccessoryDidConnect,
            object: nil
        )
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(accessoryDidDisconnect),
            name: .EAAccessoryDidDisconnect,
            object: nil
        )
        EAAccessoryManager.shared().registerForLocalNotifications()
    }

    func refreshAccessories() {
        accessories = EAAccessoryManager.shared().connectedAccessories
            .map { DetectedAccessory(from: $0) }
    }

    @objc private func accessoryDidConnect(_ notification: Notification) {
        refreshAccessories()
    }

    @objc private func accessoryDidDisconnect(_ notification: Notification) {
        refreshAccessories()
    }

    var accessorySummary: [[String: Any]] {
        accessories.map { $0.summary }
    }
}
