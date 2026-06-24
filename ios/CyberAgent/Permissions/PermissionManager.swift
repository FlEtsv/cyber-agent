import Foundation

enum ToolPermissionLevel: String, Codable, CaseIterable {
    case auto   = "auto"
    case ask    = "ask"
    case block  = "block"
}

struct ToolPermission: Identifiable, Codable {
    var id: String { toolName }
    let toolName: String
    var level: ToolPermissionLevel
    let risk: String
    let category: String
}

// Safe tools allowed on iOS without approval regardless of server default.
// Excludes anything that can modify the PC filesystem or processes.
let MOBILE_SAFE_TOOLS: Set<String> = [
    "system_info", "gpu_info", "memory_info", "list_processes",
    "network_info", "env_vars", "dns_lookup", "whois_lookup",
    "port_scan", "ping_sweep", "arp_cache", "banner_grab",
    "web_search", "web_fetch", "http_headers_check", "ssl_info",
    "encode_decode", "rag_search", "rag_add",
    "screenshot_pc", "active_window", "list_windows", "list_monitors",
    "clipboard_read",
]

let MOBILE_BLOCKED_TOOLS: Set<String> = [
    "shell", "write_file", "kill_process", "install_package", "uninstall_package",
    "restart_self", "registry_query", "check_persistence",
    "click_screen", "type_text", "hotkey", "fill_form", "credential_lookup",
    "clipboard_write",
]

@MainActor
final class PermissionManager: ObservableObject {
    static let shared = PermissionManager()

    @Published var toolPermissions: [String: ToolPermissionLevel] = [:]
    @Published var expertMode = false

    private let defaults = UserDefaults.standard

    private init() {
        load()
        expertMode = defaults.bool(forKey: Constants.Keys.expertMode)
    }

    func permission(for toolName: String) -> ToolPermissionLevel {
        if MOBILE_BLOCKED_TOOLS.contains(toolName) { return .block }
        if let saved = toolPermissions[toolName]   { return saved }
        if MOBILE_SAFE_TOOLS.contains(toolName)    { return .auto }
        return .ask
    }

    func setPermission(_ level: ToolPermissionLevel, for toolName: String) {
        toolPermissions[toolName] = level
        save()
    }

    func setExpertMode(_ enabled: Bool) {
        expertMode = enabled
        defaults.set(enabled, forKey: Constants.Keys.expertMode)
    }

    func allPermissions() -> [String: String] {
        var result: [String: String] = [:]
        MOBILE_SAFE_TOOLS.forEach   { result[$0] = "auto" }
        MOBILE_BLOCKED_TOOLS.forEach { result[$0] = "block" }
        toolPermissions.forEach      { result[$0.key] = $0.value.rawValue }
        return result
    }

    private func save() {
        let encoded = toolPermissions.mapValues { $0.rawValue }
        defaults.set(encoded, forKey: Constants.Keys.toolPerms)
    }

    private func load() {
        guard let dict = defaults.dictionary(forKey: Constants.Keys.toolPerms) as? [String: String] else { return }
        toolPermissions = dict.compactMapValues { ToolPermissionLevel(rawValue: $0) }
    }
}
