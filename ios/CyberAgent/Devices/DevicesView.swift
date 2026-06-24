import SwiftUI
import CoreBluetooth
import CoreLocation

struct DevicesView: View {
    @ObservedObject private var ble = BLEManager.shared
    @ObservedObject private var gps = GPSManager.shared
    @ObservedObject private var accessories = AccessoryDetector.shared

    var body: some View {
        ZStack {
            ChatColors.background.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 14) {
                    bluetoothSection
                    gpsSection
                    accessorySection
                }
                .padding(14)
            }
        }
        .navigationTitle("Dispositivos")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    accessories.refreshAccessories()
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .tint(ChatColors.textSecondary)
                .accessibilityLabel("Actualizar dispositivos")
            }
        }
    }

    private var bluetoothSection: some View {
        DeviceSection(title: "BLE", systemImage: "dot.radiowaves.left.and.right") {
            HStack {
                DeviceStatusDot(color: ble.state == .poweredOn ? ChatColors.success : ChatColors.danger)
                Text(bluetoothStateText)
                    .font(.system(.subheadline, design: .rounded, weight: .medium))
                    .foregroundStyle(ChatColors.textPrimary)

                Spacer()

                Button {
                    ble.isScanning ? ble.stopScan() : ble.startScan()
                } label: {
                    Label(ble.isScanning ? "Detener" : "Escanear", systemImage: ble.isScanning ? "stop.fill" : "magnifyingglass")
                }
                .buttonStyle(DeviceActionButtonStyle(color: ChatColors.accent))
                .disabled(ble.state != .poweredOn)
            }

            if let error = ble.lastError {
                Text(error)
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(ChatColors.danger)
            }

            if ble.discoveredDevices.isEmpty {
                EmptyDeviceRow(text: ble.isScanning ? "Buscando dispositivos BLE" : "Sin dispositivos BLE detectados")
            } else {
                ForEach(ble.discoveredDevices) { device in
                    Button {
                        ble.connect(to: device)
                    } label: {
                        BLEDeviceRow(device: device, isConnected: ble.connectedDevice?.id == device.id)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var gpsSection: some View {
        DeviceSection(title: "GPS", systemImage: "location") {
            HStack {
                DeviceStatusDot(color: gps.location == nil ? ChatColors.textSecondary : ChatColors.success)
                Text(locationStatusText)
                    .font(.system(.subheadline, design: .rounded, weight: .medium))
                    .foregroundStyle(ChatColors.textPrimary)

                Spacer()

                Button {
                    gps.isTracking ? gps.stopTracking() : gps.startTracking()
                } label: {
                    Label(gps.isTracking ? "Parar" : "Activar", systemImage: gps.isTracking ? "pause.fill" : "location.fill")
                }
                .buttonStyle(DeviceActionButtonStyle(color: ChatColors.accent))
            }

            if let location = gps.location {
                VStack(alignment: .leading, spacing: 6) {
                    Text(String(format: "%.6f, %.6f", location.coordinate.latitude, location.coordinate.longitude))
                        .font(.system(.body, design: .monospaced))
                        .foregroundStyle(ChatColors.textPrimary)

                    Text("Precisión \(Int(location.horizontalAccuracy)) m")
                        .font(.system(.caption, design: .rounded))
                        .foregroundStyle(ChatColors.textSecondary)

                    if let address = gps.address, !address.isEmpty {
                        Text(address)
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(ChatColors.textSecondary)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(12)
                .background(ChatColors.background)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(ChatColors.border, lineWidth: 1)
                )
            } else if let error = gps.lastError {
                Text(error)
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(ChatColors.danger)
            }
        }
    }

    private var accessorySection: some View {
        DeviceSection(title: "USB y accesorios", systemImage: "cable.connector") {
            if accessories.accessories.isEmpty {
                EmptyDeviceRow(text: "Sin accesorios externos conectados")
            } else {
                ForEach(accessories.accessories) { accessory in
                    AccessoryRow(accessory: accessory)
                }
            }
        }
    }

    private var bluetoothStateText: String {
        switch ble.state {
        case .poweredOn: return ble.isScanning ? "Escaneando" : "Bluetooth activo"
        case .poweredOff: return "Bluetooth apagado"
        case .unauthorized: return "Bluetooth sin autorización"
        case .unsupported: return "Bluetooth no soportado"
        case .resetting: return "Bluetooth reiniciando"
        default: return "Bluetooth desconocido"
        }
    }

    private var locationStatusText: String {
        if gps.isTracking { return "Seguimiento activo" }
        switch gps.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            return gps.location == nil ? "GPS autorizado" : "Ubicación disponible"
        case .denied, .restricted:
            return "GPS sin permiso"
        case .notDetermined:
            return "GPS pendiente de permiso"
        @unknown default:
            return "GPS desconocido"
        }
    }
}

private struct DeviceSection<Content: View>: View {
    let title: String
    let systemImage: String
    let content: () -> Content

    init(title: String, systemImage: String, @ViewBuilder content: @escaping () -> Content) {
        self.title = title
        self.systemImage = systemImage
        self.content = content
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: systemImage)
                    .foregroundStyle(ChatColors.accent)
                    .frame(width: 22)
                Text(title)
                    .font(.system(.headline, design: .rounded, weight: .semibold))
                    .foregroundStyle(ChatColors.textPrimary)
                Spacer()
            }

            content()
        }
        .padding(14)
        .background(ChatColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(ChatColors.border, lineWidth: 1)
        )
    }
}

private struct BLEDeviceRow: View {
    let device: BLEDevice
    let isConnected: Bool

    var body: some View {
        HStack(spacing: 10) {
            DeviceStatusDot(color: isConnected ? ChatColors.success : ChatColors.textSecondary)

            VStack(alignment: .leading, spacing: 3) {
                Text(device.displayName)
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(ChatColors.textPrimary)
                    .lineLimit(1)

                Text("\(device.signalStrength) · \(device.rssi) dBm")
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(ChatColors.textSecondary)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(ChatColors.textSecondary)
        }
        .padding(10)
        .background(ChatColors.background)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(isConnected ? ChatColors.success : ChatColors.border, lineWidth: 1)
        )
    }
}

private struct AccessoryRow: View {
    let accessory: DetectedAccessory

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                DeviceStatusDot(color: ChatColors.success)
                Text(accessory.name)
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(ChatColors.textPrimary)
                Spacer()
            }

            Text("\(accessory.manufacturer) · \(accessory.modelNumber)")
                .font(.system(.caption, design: .rounded))
                .foregroundStyle(ChatColors.textSecondary)

            if !accessory.protocolStrings.isEmpty {
                Text(accessory.protocolStrings.joined(separator: ", "))
                    .font(.system(.caption2, design: .monospaced))
                    .foregroundStyle(ChatColors.textSecondary)
                    .lineLimit(2)
            }
        }
        .padding(10)
        .background(ChatColors.background)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(ChatColors.border, lineWidth: 1)
        )
    }
}

private struct EmptyDeviceRow: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.system(.subheadline, design: .rounded))
            .foregroundStyle(ChatColors.textSecondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(ChatColors.background)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(ChatColors.border, lineWidth: 1)
            )
    }
}

private struct DeviceStatusDot: View {
    let color: Color

    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 8, height: 8)
    }
}

private struct DeviceActionButtonStyle: ButtonStyle {
    let color: Color

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(.caption, design: .rounded, weight: .semibold))
            .foregroundStyle(ChatColors.textPrimary)
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background(color.opacity(configuration.isPressed ? 0.72 : 1.0))
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}

#Preview {
    NavigationStack {
        DevicesView()
    }
    .preferredColorScheme(.dark)
}
