import Foundation

// Decides which endpoint to use: cloud relay vs LAN PC.
// Probes the local PC first (fast, low latency check) before falling back to relay.

struct EndpointProbeResult {
    let mode: ConnectionMode
    let responseTimeMs: Int
    let pcOnline: Bool
}

final class ConnectionResolver {
    static let shared = ConnectionResolver()
    private init() {}

    func bestMode() async -> ConnectionMode {
        let preferLocal = UserDefaults.standard.bool(forKey: Constants.Keys.preferLocal)
        let network     = NetworkMonitor.shared

        guard network.isOnline else { return .offline }

        if preferLocal {
            let localOK = await probeLocal()
            if localOK { return .local(ip: Constants.Local.localIP, port: Constants.Local.defaultPort) }
        }

        let relayURL = UserDefaults.standard.string(forKey: Constants.Keys.relayURL)
            ?? Constants.Relay.defaultURL
        return .relay(url: relayURL)
    }

    func probeLocal(timeoutSec: Double = 2.0) async -> Bool {
        guard let url = URL(string: "\(Constants.Local.baseURL)/api/status") else { return false }
        var req = URLRequest(url: url)
        req.timeoutInterval = timeoutSec
        do {
            let (_, resp) = try await URLSession.shared.data(for: req)
            return (resp as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func probeRelay(timeoutSec: Double = 5.0) async -> Bool {
        let relayURL = UserDefaults.standard.string(forKey: Constants.Keys.relayURL)
            ?? Constants.Relay.defaultURL
        guard let url = URL(string: "\(relayURL)/api/status") else { return false }
        var req = URLRequest(url: url)
        req.timeoutInterval = timeoutSec
        do {
            let (data, resp) = try await URLSession.shared.data(for: req)
            guard (resp as? HTTPURLResponse)?.statusCode == 200 else { return false }
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
            return json?["relay"] as? Bool == true
        } catch {
            return false
        }
    }

    func autoSwitch() async -> ConnectionMode {
        let localOK = await probeLocal()
        if localOK {
            return .local(ip: Constants.Local.localIP, port: Constants.Local.defaultPort)
        }
        let relayOK = await probeRelay()
        if relayOK {
            let relayURL = UserDefaults.standard.string(forKey: Constants.Keys.relayURL)
                ?? Constants.Relay.defaultURL
            return .relay(url: relayURL)
        }
        return .offline
    }
}
