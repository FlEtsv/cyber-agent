import Foundation
import Combine

@MainActor
final class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage]         = []
    @Published var pendingApprovals: [ToolPayload] = []
    @Published var isThinking                      = false
    @Published var connectionStatus                = "Desconectado"
    @Published var inputText                       = ""
    @Published var errorBanner: String?

    private var streamingMessageId: UUID?
    private var cancellables = Set<AnyCancellable>()

    init() {
        setupRelay()
        RelayManager.shared.connect()
    }

    // MARK: - Send

    func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        inputText = ""

        let userMsg = ChatMessage(role: .user, content: text)
        messages.append(userMsg)

        let deviceCtx = buildDeviceContext()
        RelayManager.shared.send(message: text, deviceContext: deviceCtx)
        isThinking = true
    }

    func sendImageWithText(_ imageBase64: String, text: String) {
        let full = text.isEmpty ? "[imagen adjunta]" : "\(text)\n\n[imagen]"
        inputText = full
        sendMessage()
    }

    // MARK: - Approvals

    func approve(toolId: String) {
        RelayManager.shared.approve(toolId: toolId, approved: true)
        pendingApprovals.removeAll { $0.id == toolId }
    }

    func reject(toolId: String) {
        RelayManager.shared.approve(toolId: toolId, approved: false)
        pendingApprovals.removeAll { $0.id == toolId }
    }

    func stopAgent() {
        RelayManager.shared.stop()
        isThinking = false
    }

    // MARK: - Relay setup

    private func setupRelay() {
        RelayManager.shared.onEvent = { [weak self] event in
            Task { @MainActor in self?.handle(event) }
        }

        RelayManager.shared.$connectionLabel
            .receive(on: RunLoop.main)
            .assign(to: &$connectionStatus)
    }

    private func handle(_ event: AgentEvent) {
        switch event.type {
        case .connected:
            errorBanner = nil

        case .token:
            guard case .string(let text) = event.data else { return }
            if let id = streamingMessageId,
               let idx = messages.firstIndex(where: { $0.id == id }) {
                messages[idx].content += text
            } else {
                let msg = ChatMessage(role: .assistant, content: text, state: .streaming)
                messages.append(msg)
                streamingMessageId = msg.id
            }

        case .done:
            if let id = streamingMessageId,
               let idx = messages.firstIndex(where: { $0.id == id }) {
                messages[idx].state = .done
            }
            streamingMessageId = nil
            isThinking         = false

        case .error:
            let errText = (event.data.flatMap { if case .string(let s) = $0 { return s } else { return nil } }) ?? "Error"
            if let id = streamingMessageId,
               let idx = messages.firstIndex(where: { $0.id == id }) {
                messages[idx].state = .error
                messages[idx].content += "\n\n⚠️ \(errText)"
            } else {
                messages.append(ChatMessage(role: .assistant, content: "⚠️ \(errText)", state: .error))
            }
            streamingMessageId = nil
            isThinking         = false

        case .needApproval:
            if case .string(let raw) = event.data,
               let data = raw.data(using: .utf8),
               let payload = try? JSONDecoder().decode(ToolPayload.self, from: data) {
                pendingApprovals.append(payload)
            }

        case .toolCall:
            isThinking = true

        case .toolResult:
            break

        case .status:
            break

        case .sessionClosed:
            isThinking = false
            pendingApprovals.removeAll()
        }
    }

    // MARK: - Device context

    private func buildDeviceContext() -> String {
        var parts: [String] = ["iPhone"]
        let ble = BLEManager.shared
        let gps = GPSManager.shared
        let acc = AccessoryDetector.shared

        if let connected = ble.connectedDevice {
            parts.append("BLE:\(connected.displayName)")
        } else if !ble.discoveredDevices.isEmpty {
            parts.append("\(ble.discoveredDevices.count) BLE devices")
        }
        if let loc = gps.location {
            parts.append("GPS:\(String(format: "%.4f", loc.coordinate.latitude)),\(String(format: "%.4f", loc.coordinate.longitude))")
        }
        if !acc.accessories.isEmpty {
            parts.append("\(acc.accessories.count) accesorios USB")
        }
        return parts.joined(separator: " | ")
    }

    func clearHistory() {
        messages.removeAll()
        streamingMessageId = nil
    }
}
