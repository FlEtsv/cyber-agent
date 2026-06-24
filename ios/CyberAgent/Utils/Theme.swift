import SwiftUI

enum CAColors {
    static let backgroundPrimary = Color(red: 13 / 255, green: 17 / 255, blue: 23 / 255)
    static let backgroundSecondary = Color(red: 22 / 255, green: 27 / 255, blue: 34 / 255)
    static let accent = Color(red: 88 / 255, green: 166 / 255, blue: 255 / 255)
    static let dangerRed = Color(red: 248 / 255, green: 81 / 255, blue: 73 / 255)
    static let successGreen = Color(red: 63 / 255, green: 185 / 255, blue: 80 / 255)
    static let textPrimary = Color.white
    static let textSecondary = Color(red: 139 / 255, green: 148 / 255, blue: 158 / 255)
    static let borderColor = Color(red: 48 / 255, green: 54 / 255, blue: 61 / 255)
}

enum CAFont {
    static let body = Font.system(.body, design: .rounded)
    static let bodyMedium = Font.system(.body, design: .rounded, weight: .medium)
    static let headline = Font.system(.headline, design: .rounded, weight: .semibold)
    static let caption = Font.system(.caption, design: .rounded)
    static let captionMedium = Font.system(.caption, design: .rounded, weight: .medium)
    static let monoBody = Font.system(.body, design: .monospaced)
    static let monoCaption = Font.system(.caption, design: .monospaced)
}

struct StatusDot: View {
    let color: Color

    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 8, height: 8)
            .accessibilityHidden(true)
    }
}

struct CAButton: View {
    enum Style {
        case primary
        case danger
        case ghost
    }

    let label: String
    let systemImage: String?
    let style: Style
    let action: () -> Void

    init(
        _ label: String,
        systemImage: String? = nil,
        style: Style = .primary,
        action: @escaping () -> Void
    ) {
        self.label = label
        self.systemImage = systemImage
        self.style = style
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 7) {
                if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(label)
            }
            .font(CAFont.bodyMedium)
            .foregroundStyle(foreground)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .padding(.horizontal, 12)
            .background(background)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(border, lineWidth: 1)
            )
        }
    }

    private var foreground: Color {
        switch style {
        case .primary, .danger:
            return CAColors.textPrimary
        case .ghost:
            return CAColors.accent
        }
    }

    private var background: Color {
        switch style {
        case .primary:
            return CAColors.accent
        case .danger:
            return CAColors.dangerRed
        case .ghost:
            return Color.clear
        }
    }

    private var border: Color {
        switch style {
        case .primary:
            return CAColors.accent
        case .danger:
            return CAColors.dangerRed
        case .ghost:
            return CAColors.borderColor
        }
    }
}

#Preview {
    VStack(spacing: 14) {
        HStack {
            StatusDot(color: CAColors.successGreen)
            Text("Conectado")
                .font(CAFont.captionMedium)
                .foregroundStyle(CAColors.textSecondary)
        }
        CAButton("Primario", systemImage: "checkmark", action: {})
        CAButton("Peligro", systemImage: "xmark", style: .danger, action: {})
        CAButton("Fantasma", systemImage: "gear", style: .ghost, action: {})
    }
    .padding()
    .background(CAColors.backgroundPrimary)
    .preferredColorScheme(.dark)
}
