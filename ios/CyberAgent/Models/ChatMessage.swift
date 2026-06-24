import Foundation

enum MessageRole: String, Codable {
    case user, assistant, tool, system
}

enum MessageState {
    case streaming, done, error
}

struct ChatMessage: Identifiable, Codable {
    let id: UUID
    var role: MessageRole
    var content: String
    var timestamp: Date
    var state: MessageState = .done
    var toolCalls: [ToolCallRecord]?
    var imageData: [Data]?

    init(id: UUID = UUID(), role: MessageRole, content: String,
         timestamp: Date = Date(), state: MessageState = .done) {
        self.id        = id
        self.role      = role
        self.content   = content
        self.timestamp = timestamp
        self.state     = state
    }

    private enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp, toolCalls
    }
}

struct ToolCallRecord: Identifiable, Codable {
    let id: String
    let name: String
    let args: [String: AnyCodable]
    var result: AnyCodable?
    var approved: Bool?
}

struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) { self.value = value }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let v = try? container.decode(Bool.self)   { value = v; return }
        if let v = try? container.decode(Int.self)    { value = v; return }
        if let v = try? container.decode(Double.self) { value = v; return }
        if let v = try? container.decode(String.self) { value = v; return }
        if let v = try? container.decode([String: AnyCodable].self) { value = v; return }
        if let v = try? container.decode([AnyCodable].self) { value = v; return }
        value = NSNull()
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch value {
        case let v as Bool:                   try container.encode(v)
        case let v as Int:                    try container.encode(v)
        case let v as Double:                 try container.encode(v)
        case let v as String:                 try container.encode(v)
        case let v as [String: AnyCodable]:   try container.encode(v)
        case let v as [AnyCodable]:           try container.encode(v)
        default:                              try container.encodeNil()
        }
    }
}
