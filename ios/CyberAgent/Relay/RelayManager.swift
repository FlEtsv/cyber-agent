import Foundation
import Combine

@MainActor
final class RelayManager: ObservableObject {
    static let shared = RelayManager()

    @Published var isConnected     = false
    @Published var isPCOnline      = false
    @Published var connectionLabel = "Desconectado"
    @Published var sessionId: String?

    var onEvent: ((AgentEvent) -> Void)?

    private var task: URLSessionWebSocketTask?
    private var retryCount = 0
    private let maxRetry   = 8
    private var retryTask: Task<Void, Never>?
    private var keepAliveTask: Task<Void, Never>?

    private init() {}

    func connect() {
        retryTask?.cancel()
        retryTask = Task { await _connect() }
    }

    func disconnect() {
        retryTask?.cancel()
        keepAliveTask?.cancel()
        task?.cancel(with: .goingAway, reason: nil)
        task      = nil
        isConnected = false
        connectionLabel = "Desconectado"
    }

    func send(message: String, deviceContext: String = "iPhone") {
        let payload: [String: Any] = [
            "type":    "message",
            "content": message,
            "device":  deviceContext,
            "expert_mode": false,
        ]
        sendJSON(payload)
    }

    func approve(toolId: String, approved: Bool) {
        sendJSON(["type": "approve", "tool_id": toolId, "approved": approved])
    }

    func stop() {
        sendJSON(["type": "stop"])
    }

    private func sendJSON(_ dict: [String: Any]) {
        guard let task else { return }
        guard let data = try? JSONSerialization.data(withJSONObject: dict),
              let text = String(data: data, encoding: .utf8) else { return }
        task.send(.string(text)) { _ in }
    }

    private func _connect() async {
        let mode = NetworkMonitor.shared.connectionMode
        let wsURL = mode.wsURL
        guard !wsURL.isEmpty, let url = URL(string: wsURL) else {
            connectionLabel = "Sin conexión"
            return
        }

        var request = URLRequest(url: url)
        if let token = AuthManager.shared.token {
            request.setValue("ca_token=\(token)", forHTTPHeaderField: "Cookie")
        }

        let session = URLSession(configuration: .default)
        let newTask = session.webSocketTask(with: request)
        self.task   = newTask
        newTask.resume()
        connectionLabel = "Conectando…"

        startReceiving(task: newTask)
        startKeepAlive(task: newTask)
    }

    private func startReceiving(task: URLSessionWebSocketTask) {
        Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                do {
                    let msg = try await task.receive()
                    self.retryCount = 0
                    switch msg {
                    case .string(let text):
                        self.handleText(text)
                    case .data(let data):
                        if let text = String(data: data, encoding: .utf8) {
                            self.handleText(text)
                        }
                    @unknown default:
                        break
                    }
                } catch {
                    self.isConnected = false
                    self.connectionLabel = "Reconectando…"
                    await self.scheduleRetry()
                    break
                }
            }
        }
    }

    private func startKeepAlive(task: URLSessionWebSocketTask) {
        keepAliveTask?.cancel()
        keepAliveTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 20_000_000_000) // 20s
                task.sendPing { _ in }
            }
        }
    }

    private func scheduleRetry() async {
        retryCount = min(retryCount + 1, maxRetry)
        let delay = min(Double(1 << retryCount), 60.0) // 2, 4, 8, 16, 32, 60s cap
        try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
        await _connect()
    }

    private func handleText(_ text: String) {
        guard let data  = text.data(using: .utf8),
              let json  = try? JSONDecoder().decode([String: AnyDecodable].self, from: data),
              let typeStr = json["type"]?.string,
              let type  = AgentEventType(rawValue: typeStr) else { return }

        let rawData  = json["data"]
        let event: AgentEvent

        switch type {
        case .connected:
            isConnected     = true
            connectionLabel = NetworkMonitor.shared.connectionMode.displayName
            if let obj = rawData?.dict {
                isPCOnline  = obj["pc_online"]?.bool ?? false
                sessionId   = obj["session_id"]?.string
            }
            event = AgentEvent(type: .connected, data: nil)

        case .sessionClosed:
            isPCOnline = false
            event = AgentEvent(type: .sessionClosed, data: nil)

        default:
            event = AgentEvent(type: type,
                               data: rawData.flatMap { .string($0.string ?? "") })
        }

        onEvent?(event)
    }
}

struct AnyDecodable: Decodable {
    var string: String?
    var bool: Bool?
    var dict: [String: AnyDecodable]?
    var array: [AnyDecodable]?

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let v = try? c.decode(String.self) { string = v; return }
        if let v = try? c.decode(Bool.self)   { bool = v; return }
        if let v = try? c.decode([String: AnyDecodable].self) { dict = v; return }
        if let v = try? c.decode([AnyDecodable].self)         { array = v; return }
    }
}
