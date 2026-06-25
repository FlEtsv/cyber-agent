import Foundation
import Combine

@MainActor
final class AuthManager: ObservableObject {
    static let shared = AuthManager()

    @Published var isAuthenticated = false
    @Published var isLoading       = false
    @Published var errorMessage: String?
    @Published var totpRequired    = false

    private var baseURL: String { resolvedBaseURL() }
    private let session = URLSession.shared

    private init() {
        checkExistingToken()
    }

    private func resolvedBaseURL() -> String {
        NetworkMonitor.shared.isOnline
            ? (UserDefaults.standard.string(forKey: Constants.Keys.relayURL) ?? Constants.Relay.defaultURL)
            : Constants.Local.baseURL
    }

    func checkStatus() async {
        guard let url = URL(string: baseURL + Constants.Relay.statusPath) else { return }
        do {
            let (data, _) = try await session.data(from: url)
            let json = try JSONDecoder().decode([String: AnyCodableSimple].self, from: data)
            totpRequired = json["totp_required"]?.bool ?? false
        } catch {}
    }

    func login(email: String, password: String, totp: String) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        guard let url = URL(string: baseURL + Constants.Relay.loginPath) else { return false }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: String] = ["email": email, "password": password, "totp": totp]
        req.httpBody = try? JSONEncoder().encode(body)

        do {
            let (data, resp) = try await session.data(for: req)
            guard let http = resp as? HTTPURLResponse, http.statusCode == 200 else {
                let json = try? JSONDecoder().decode([String: AnyCodableSimple].self, from: data)
                errorMessage = json?["error"]?.string ?? "Error de autenticación"
                return false
            }
            let json = try JSONDecoder().decode([String: AnyCodableSimple].self, from: data)
            guard json["ok"]?.bool == true else {
                errorMessage = json["error"]?.string ?? "Credenciales incorrectas"
                return false
            }
            if let cookie = extractCookie(from: resp, name: Constants.Keys.jwtCookie) {
                KeychainHelper.shared.save(cookie, key: Constants.Keychain.tokenKey)
                isAuthenticated = true
                return true
            }
            errorMessage = "No se recibió token de sesión"
            return false
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func logout() {
        KeychainHelper.shared.delete(key: Constants.Keychain.tokenKey)
        isAuthenticated = false
        Task { await sendLogout() }
    }

    var token: String? {
        KeychainHelper.shared.load(key: Constants.Keychain.tokenKey)
    }

    private func checkExistingToken() {
        isAuthenticated = KeychainHelper.shared.load(key: Constants.Keychain.tokenKey) != nil
    }

    private func extractCookie(from response: URLResponse, name: String) -> String? {
        guard let http = response as? HTTPURLResponse,
              let fields = http.allHeaderFields as? [String: String],
              let url = response.url else { return nil }
        let cookies = HTTPCookie.cookies(withResponseHeaderFields: fields, for: url)
        return cookies.first(where: { $0.name == name })?.value
    }

    private func sendLogout() async {
        guard let url = URL(string: baseURL + Constants.Relay.logoutPath) else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        if let token = token {
            req.setValue("ca_token=\(token)", forHTTPHeaderField: "Cookie")
        }
        try? await session.data(for: req)
    }
}

struct AnyCodableSimple: Codable {
    let bool: Bool?
    let string: String?

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let v = try? c.decode(Bool.self)   { bool = v; string = nil; return }
        if let v = try? c.decode(String.self) { string = v; bool = nil; return }
        bool = nil; string = nil
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        if let b = bool         { try c.encode(b) }
        else if let s = string  { try c.encode(s) }
        else                    { try c.encodeNil() }
    }
}
