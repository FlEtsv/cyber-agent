import SwiftUI

struct MessageBubble: View {
    let message: ChatMessage

    private var isUser: Bool {
        message.role == .user
    }

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            if isUser { Spacer(minLength: 48) }

            VStack(alignment: isUser ? .trailing : .leading, spacing: 6) {
                Text(Self.markdown(message.content))
                    .font(.system(.body, design: .rounded))
                    .foregroundStyle(ChatColors.textPrimary)
                    .textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)

                HStack(spacing: 6) {
                    if message.state == .streaming {
                        ProgressView()
                            .controlSize(.mini)
                            .tint(ChatColors.accent)
                    }

                    Text(Self.timeFormatter.string(from: message.timestamp))
                        .font(.system(.caption2, design: .rounded))
                        .foregroundStyle(ChatColors.textSecondary)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(isUser ? ChatColors.userBubble : ChatColors.assistantBubble)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(message.state == .error ? ChatColors.danger : ChatColors.border, lineWidth: 1)
            )

            if !isUser { Spacer(minLength: 48) }
        }
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }

    private static func markdown(_ content: String) -> AttributedString {
        (try? AttributedString(markdown: content)) ?? AttributedString(content)
    }

    private static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter
    }()
}

enum ChatColors {
    static let background = Color(red: 13 / 255, green: 17 / 255, blue: 23 / 255)
    static let surface = Color(red: 22 / 255, green: 27 / 255, blue: 34 / 255)
    static let border = Color(red: 48 / 255, green: 54 / 255, blue: 61 / 255)
    static let accent = Color(red: 88 / 255, green: 166 / 255, blue: 255 / 255)
    static let danger = Color(red: 248 / 255, green: 81 / 255, blue: 73 / 255)
    static let success = Color(red: 63 / 255, green: 185 / 255, blue: 80 / 255)
    static let textPrimary = Color.white
    static let textSecondary = Color(red: 139 / 255, green: 148 / 255, blue: 158 / 255)
    static let userBubble = Color(red: 31 / 255, green: 111 / 255, blue: 235 / 255)
    static let assistantBubble = Color(red: 22 / 255, green: 27 / 255, blue: 34 / 255)
}
