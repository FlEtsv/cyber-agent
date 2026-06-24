import Foundation

enum Constants {
    enum Relay {
        static let defaultURL = "https://cyberagent-relay-819820880956.us-central1.run.app"
        static let wsPath     = "/ws"
        static let loginPath  = "/api/auth/login"
        static let statusPath = "/api/auth/status"
        static let apiStatus  = "/api/status"
        static let logoutPath = "/api/auth/logout"
    }

    enum Local {
        static let defaultPort: Int = 8765
        static var baseURL: String {
            "http://\(localIP):\(defaultPort)"
        }
        static var wsURL: String {
            "ws://\(localIP):\(defaultPort)/ws"
        }
        static var localIP: String {
            UserDefaults.standard.string(forKey: Keys.localIP) ?? "192.168.18.240"
        }
    }

    enum Keys {
        static let jwtCookie   = "ca_token"
        static let localIP     = "cyberagent.local_ip"
        static let relayURL    = "cyberagent.relay_url"
        static let preferLocal = "cyberagent.prefer_local"
        static let expertMode  = "cyberagent.expert_mode"
        static let toolPerms   = "cyberagent.tool_permissions"
    }

    enum Keychain {
        static let service  = "com.cyberagent.ios"
        static let tokenKey = "relay_jwt"
    }

    enum BLE {
        static let scanDuration: TimeInterval = 10
    }

    enum LLM {
        static let localModelName = "cyberagent-mini"
        static let maxTokens      = 512
        static let temperature    = 0.7
    }

    enum UI {
        static let bubbleCornerRadius: CGFloat = 16
        static let approvalCardRadius: CGFloat = 12
        static let animationDuration           = 0.25
    }
}
