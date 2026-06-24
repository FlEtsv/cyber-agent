import SwiftUI
import Combine

struct ToolApprovalCard: View {
    let payload: ToolPayload
    let approve: () -> Void
    let reject: () -> Void

    @State private var remainingSeconds = 60
    @State private var didResolve = false

    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            header

            if !argsText.isEmpty {
                Text(argsText)
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(ChatColors.textSecondary)
                    .lineLimit(6)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(10)
                    .background(ChatColors.background)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(ChatColors.border, lineWidth: 1)
                    )
            }

            HStack(spacing: 10) {
                Button("Rechazar") {
                    resolve(reject)
                }
                .buttonStyle(ToolApprovalButtonStyle(color: ChatColors.danger))

                Button("Aprobar") {
                    resolve(approve)
                }
                .buttonStyle(ToolApprovalButtonStyle(color: ChatColors.success))
            }
        }
        .padding(14)
        .background(ChatColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(riskColor, lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.35), radius: 18, x: 0, y: 10)
        .onReceive(timer) { _ in
            guard !didResolve else { return }
            if remainingSeconds <= 1 {
                resolve(reject)
            } else {
                remainingSeconds -= 1
            }
        }
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 10) {
            VStack(alignment: .leading, spacing: 8) {
                Text(payload.name)
                    .font(.system(.headline, design: .rounded, weight: .semibold))
                    .foregroundStyle(ChatColors.textPrimary)
                    .lineLimit(2)

                HStack(spacing: 6) {
                    if let category = payload.category, !category.isEmpty {
                        badge(category, color: ChatColors.accent)
                    }
                    badge((payload.risk ?? "riesgo").uppercased(), color: riskColor)
                }
            }

            Spacer()

            ZStack {
                Circle()
                    .stroke(ChatColors.border, lineWidth: 4)
                Circle()
                    .trim(from: 0, to: CGFloat(remainingSeconds) / 60)
                    .stroke(riskColor, style: StrokeStyle(lineWidth: 4, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                Text("\(remainingSeconds)")
                    .font(.system(.caption2, design: .monospaced, weight: .bold))
                    .foregroundStyle(ChatColors.textPrimary)
            }
            .frame(width: 42, height: 42)
            .accessibilityLabel("Cuenta atrás \(remainingSeconds) segundos")
        }
    }

    private func badge(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(.caption2, design: .monospaced, weight: .bold))
            .foregroundStyle(color)
            .padding(.horizontal, 7)
            .padding(.vertical, 4)
            .background(color.opacity(0.12))
            .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
    }

    private var riskColor: Color {
        switch payload.risk?.lowercased() {
        case "high", "alto", "danger", "dangerous", "critical", "critico":
            return ChatColors.danger
        default:
            return ChatColors.success
        }
    }

    private var argsText: String {
        guard !payload.args.isEmpty else { return "{}" }
        if let data = try? JSONEncoder().encode(payload.args),
           let text = String(data: data, encoding: .utf8) {
            return text
        }
        return payload.args.keys.sorted().joined(separator: ", ")
    }

    private func resolve(_ action: () -> Void) {
        guard !didResolve else { return }
        didResolve = true
        action()
    }
}

private struct ToolApprovalButtonStyle: ButtonStyle {
    let color: Color

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(.subheadline, design: .rounded, weight: .semibold))
            .foregroundStyle(ChatColors.textPrimary)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .background(color.opacity(configuration.isPressed ? 0.72 : 1.0))
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}

#Preview {
    ToolApprovalCard(
        payload: ToolPayload(
            id: "preview",
            name: "shell_command",
            args: ["command": AnyCodable("dir")],
            category: "system",
            risk: "high",
            defaultPermission: nil
        ),
        approve: {},
        reject: {}
    )
    .padding()
    .background(ChatColors.background)
    .preferredColorScheme(.dark)
}
