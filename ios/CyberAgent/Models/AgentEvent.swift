import Foundation

enum AgentEventType: String, Codable {
    case connected, token, toolCall = "tool_call", toolResult = "tool_result"
    case needApproval = "need_approval", done, error, status, sessionClosed = "session_closed"
}

struct AgentEvent: Codable {
    let type: AgentEventType
    let data: AgentEventData?
}

enum AgentEventData: Codable {
    case string(String)
    case toolPayload(ToolPayload)
    case connectedPayload(ConnectedPayload)
    case toolResult(ToolResultPayload)
    case raw([String: AnyCodable])

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let s = try? container.decode(String.self)             { self = .string(s); return }
        if let p = try? container.decode(ToolPayload.self)         { self = .toolPayload(p); return }
        if let p = try? container.decode(ConnectedPayload.self)    { self = .connectedPayload(p); return }
        if let p = try? container.decode(ToolResultPayload.self)   { self = .toolResult(p); return }
        let raw = (try? container.decode([String: AnyCodable].self)) ?? [:]
        self = .raw(raw)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let s):             try container.encode(s)
        case .toolPayload(let p):        try container.encode(p)
        case .connectedPayload(let p):   try container.encode(p)
        case .toolResult(let p):         try container.encode(p)
        case .raw(let r):                try container.encode(r)
        }
    }
}

struct ToolPayload: Codable, Identifiable {
    let id: String
    let name: String
    let args: [String: AnyCodable]
    let category: String?
    let risk: String?
    let defaultPermission: String?

    enum CodingKeys: String, CodingKey {
        case id, name, args, category, risk
        case defaultPermission = "default_permission"
    }
}

struct ConnectedPayload: Codable {
    let relay: Bool?
    let pcOnline: Bool?
    let models: [String]?
    let sessionId: String?
    let device: String?

    enum CodingKeys: String, CodingKey {
        case relay, models, device
        case pcOnline = "pc_online"
        case sessionId = "session_id"
    }
}

struct ToolResultPayload: Codable {
    let id: String
    let result: [String: AnyCodable]
}
