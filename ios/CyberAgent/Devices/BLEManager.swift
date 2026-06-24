import Foundation
import CoreBluetooth
import Combine

struct BLEDevice: Identifiable, Equatable {
    let id: UUID
    let name: String
    let rssi: Int
    var isConnected: Bool
    var services: [String]
    var characteristics: [String: String]

    var displayName: String { name.isEmpty ? "Dispositivo \(id.uuidString.prefix(8))" : name }
    var signalStrength: String {
        switch rssi {
        case -50...0:   return "Excelente"
        case -70 ..< -50: return "Buena"
        case -90 ..< -70: return "Débil"
        default:         return "Muy débil"
        }
    }
}

@MainActor
final class BLEManager: NSObject, ObservableObject {
    static let shared = BLEManager()

    @Published var state: CBManagerState = .unknown
    @Published var discoveredDevices: [BLEDevice] = []
    @Published var connectedDevice: BLEDevice?
    @Published var isScanning = false
    @Published var lastError: String?

    private var centralManager: CBCentralManager!
    private var activePeripheral: CBPeripheral?
    private var peripheralMap: [UUID: CBPeripheral] = [:]
    private var scanTimer: Timer?

    override private init() {
        super.init()
        centralManager = CBCentralManager(delegate: self, queue: nil)
    }

    func startScan(duration: TimeInterval = 10) {
        guard state == .poweredOn else {
            lastError = "Bluetooth no disponible (estado: \(state.rawValue))"
            return
        }
        isScanning = true
        discoveredDevices.removeAll()
        centralManager.scanForPeripherals(withServices: nil, options: [
            CBCentralManagerScanOptionAllowDuplicatesKey: false,
        ])
        scanTimer?.invalidate()
        scanTimer = Timer.scheduledTimer(withTimeInterval: duration, repeats: false) { [weak self] _ in
            Task { @MainActor in self?.stopScan() }
        }
    }

    func stopScan() {
        centralManager.stopScan()
        isScanning = false
        scanTimer?.invalidate()
    }

    func connect(to device: BLEDevice) {
        guard let peripheral = peripheralMap[device.id] else { return }
        activePeripheral = peripheral
        centralManager.connect(peripheral, options: nil)
    }

    func disconnect() {
        if let p = activePeripheral { centralManager.cancelPeripheralConnection(p) }
    }

    var deviceSummary: [String: Any] {
        [
            "bluetooth_state":   stateDescription,
            "discovered_count":  discoveredDevices.count,
            "connected_device":  connectedDevice.map { ["name": $0.displayName, "rssi": $0.rssi] } as Any,
            "devices":           discoveredDevices.map { ["name": $0.displayName, "rssi": $0.rssi,
                                                          "connected": $0.isConnected] },
        ]
    }

    private var stateDescription: String {
        switch state {
        case .poweredOn:   return "encendido"
        case .poweredOff:  return "apagado"
        case .unauthorized: return "sin autorización"
        case .unsupported: return "no soportado"
        default:           return "desconocido"
        }
    }
}

extension BLEManager: CBCentralManagerDelegate {
    nonisolated func centralManagerDidUpdateState(_ central: CBCentralManager) {
        Task { @MainActor in self.state = central.state }
    }

    nonisolated func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral,
                         advertisementData: [String: Any], rssi RSSI: NSNumber) {
        let uuid = peripheral.identifier
        let name = peripheral.name ?? ""
        Task { @MainActor in
            self.peripheralMap[uuid] = peripheral
            if let idx = self.discoveredDevices.firstIndex(where: { $0.id == uuid }) {
                self.discoveredDevices[idx] = BLEDevice(id: uuid, name: name, rssi: RSSI.intValue,
                                                         isConnected: false, services: [], characteristics: [:])
            } else {
                self.discoveredDevices.append(BLEDevice(id: uuid, name: name, rssi: RSSI.intValue,
                                                         isConnected: false, services: [], characteristics: [:]))
            }
        }
    }

    nonisolated func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        Task { @MainActor in
            self.connectedDevice = self.discoveredDevices.first(where: { $0.id == peripheral.identifier })
            peripheral.delegate = self
            peripheral.discoverServices(nil)
        }
    }

    nonisolated func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral,
                         error: Error?) {
        Task { @MainActor in self.connectedDevice = nil }
    }

    nonisolated func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral,
                         error: Error?) {
        Task { @MainActor in self.lastError = error?.localizedDescription ?? "Error de conexión BLE" }
    }
}

extension BLEManager: CBPeripheralDelegate {
    nonisolated func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard let services = peripheral.services else { return }
        Task { @MainActor in
            if let idx = self.discoveredDevices.firstIndex(where: { $0.id == peripheral.identifier }) {
                self.discoveredDevices[idx].services = services.map { $0.uuid.uuidString }
            }
        }
        for service in services {
            peripheral.discoverCharacteristics(nil, for: service)
        }
    }

    nonisolated func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService,
                     error: Error?) {
        guard let chars = service.characteristics else { return }
        for char in chars where char.properties.contains(.read) {
            peripheral.readValue(for: char)
        }
    }

    nonisolated func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic,
                     error: Error?) {
        guard let data = characteristic.value,
              let text = String(data: data, encoding: .utf8) else { return }
        Task { @MainActor in
            if let idx = self.discoveredDevices.firstIndex(where: { $0.id == peripheral.identifier }) {
                self.discoveredDevices[idx].characteristics[characteristic.uuid.uuidString] = text
            }
        }
    }
}
