import Foundation

// Executes simple tool calls on-device when the relay is unreachable.
// Only allows MOBILE_SAFE_TOOLS. Any blocked tool returns an explicit rejection.

@MainActor
final class OfflineAgentRunner {
    static let shared = OfflineAgentRunner()
    private init() {}

    struct RunResult {
        let response: String
        let toolsUsed: [String]
    }

    func run(userMessage: String, history: [[String: String]]) async -> RunResult {
        let llm = LocalLLMManager.shared
        var toolsUsed: [String] = []
        var responseText = ""

        do {
            let result = try await llm.generate(prompt: userMessage, history: history)
            responseText = result.text

            for toolName in result.toolCalls {
                let toolResult = await executeSafeTool(toolName)
                responseText += "\n\n**\(toolName):** \(toolResult)"
                toolsUsed.append(toolName)
            }
        } catch {
            responseText = "Error en el modo local: \(error.localizedDescription)"
        }

        return RunResult(response: responseText, toolsUsed: toolsUsed)
    }

    private func executeSafeTool(_ name: String) async -> String {
        guard MOBILE_SAFE_TOOLS.contains(name) else {
            return "⛔ Herramienta '\(name)' no disponible en modo offline."
        }

        switch name {
        case "gps_location":
            let summary = GPSManager.shared.currentLocationSummary()
            return formatJSON(summary)

        case "ble_devices":
            let ble = BLEManager.shared
            let devices = ble.discoveredDevices.map { ["name": $0.displayName, "rssi": $0.rssi] }
            return "Dispositivos BLE (\(devices.count)): \(formatJSON(["devices": devices]))"

        case "usb_accessories":
            let acc = AccessoryDetector.shared
            return "Accesorios (\(acc.accessories.count)): \(formatJSON(["accessories": acc.accessorySummary]))"

        default:
            return "ℹ️ Herramienta '\(name)' disponible en PC. Conecta al relay para usarla."
        }
    }

    private func formatJSON(_ dict: [String: Any]) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: dict, options: .prettyPrinted),
              let text = String(data: data, encoding: .utf8) else { return dict.description }
        return text
    }
}
