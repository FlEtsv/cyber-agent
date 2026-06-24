import Foundation
import Network
import Combine

enum ConnectionMode {
    case relay(url: String)
    case local(ip: String, port: Int)
    case offline

    var wsURL: String {
        switch self {
        case .relay(let url):
            return url.replacingOccurrences(of: "https://", with: "wss://")
                      .replacingOccurrences(of: "http://", with: "ws://") + "/ws"
        case .local(let ip, let port):
            return "ws://\(ip):\(port)/ws"
        case .offline:
            return ""
        }
    }

    var displayName: String {
        switch self {
        case .relay:   return "Cloud Run Relay"
        case .local:   return "Red local (LAN)"
        case .offline: return "Sin conexión"
        }
    }
}

@MainActor
final class NetworkMonitor: ObservableObject {
    static let shared = NetworkMonitor()

    @Published var isOnline = false
    @Published var connectionMode: ConnectionMode = .offline

    private let monitor = NWPathMonitor()
    private let queue   = DispatchQueue(label: "net.monitor")

    private init() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isOnline = path.status == .satisfied
                self?.resolveMode()
            }
        }
        monitor.start(queue: queue)
    }

    func resolveMode() {
        if !isOnline {
            connectionMode = .offline
            return
        }
        let preferLocal = UserDefaults.standard.bool(forKey: Constants.Keys.preferLocal)
        if preferLocal {
            connectionMode = .local(ip: Constants.Local.localIP, port: Constants.Local.defaultPort)
        } else {
            let relayURL = UserDefaults.standard.string(forKey: Constants.Keys.relayURL)
                ?? Constants.Relay.defaultURL
            connectionMode = .relay(url: relayURL)
        }
    }

    func switchToLocal() {
        UserDefaults.standard.set(true, forKey: Constants.Keys.preferLocal)
        resolveMode()
    }

    func switchToRelay() {
        UserDefaults.standard.set(false, forKey: Constants.Keys.preferLocal)
        resolveMode()
    }
}
