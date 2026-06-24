import SwiftUI
import UIKit

struct SettingsView: View {
    @ObservedObject private var auth = AuthManager.shared
    @ObservedObject private var network = NetworkMonitor.shared
    @ObservedObject private var permissions = PermissionManager.shared

    @State private var relayURL = UserDefaults.standard.string(forKey: Constants.Keys.relayURL) ?? Constants.Relay.defaultURL
    @State private var localIP = UserDefaults.standard.string(forKey: Constants.Keys.localIP) ?? Constants.Local.localIP
    @State private var preferLocal = UserDefaults.standard.bool(forKey: Constants.Keys.preferLocal)

    private var toolNames: [String] {
        Array(MOBILE_SAFE_TOOLS.union(MOBILE_BLOCKED_TOOLS).union(Set(permissions.toolPermissions.keys))).sorted()
    }

    var body: some View {
        ZStack {
            ChatColors.background.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 14) {
                    connectionSection
                    permissionSection
                    sessionSection
                }
                .padding(14)
            }
        }
        .navigationTitle("Ajustes")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var connectionSection: some View {
        SettingsSection(title: "Conexión", systemImage: "network") {
            VStack(spacing: 10) {
                SettingsTextField(title: "Relay", text: $relayURL, keyboard: .URL)
                SettingsTextField(title: "PC local", text: $localIP, keyboard: .numbersAndPunctuation)

                Toggle(isOn: Binding(
                    get: { preferLocal },
                    set: { value in
                        preferLocal = value
                        UserDefaults.standard.set(value, forKey: Constants.Keys.preferLocal)
                        network.resolveMode()
                    }
                )) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Preferir red local")
                            .foregroundStyle(ChatColors.textPrimary)
                        Text(network.connectionMode.displayName)
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(ChatColors.textSecondary)
                    }
                }
                .tint(ChatColors.accent)

                Button {
                    saveConnection()
                } label: {
                    Label("Guardar conexión", systemImage: "checkmark")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(SettingsButtonStyle(color: ChatColors.accent))
            }
        }
    }

    private var permissionSection: some View {
        SettingsSection(title: "Permisos", systemImage: "slider.horizontal.3") {
            VStack(spacing: 12) {
                Toggle(isOn: Binding(
                    get: { permissions.expertMode },
                    set: { permissions.setExpertMode($0) }
                )) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Modo experto")
                            .foregroundStyle(ChatColors.textPrimary)
                        Text("Solo para herramientas permitidas en iOS")
                            .font(.system(.caption, design: .rounded))
                            .foregroundStyle(ChatColors.textSecondary)
                    }
                }
                .tint(ChatColors.danger)

                ForEach(toolNames, id: \.self) { tool in
                    HStack(spacing: 10) {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(tool)
                                .font(.system(.subheadline, design: .monospaced, weight: .semibold))
                                .foregroundStyle(ChatColors.textPrimary)
                                .lineLimit(1)

                            Text(toolKind(tool))
                                .font(.system(.caption2, design: .rounded))
                                .foregroundStyle(ChatColors.textSecondary)
                        }

                        Spacer()

                        Picker("", selection: permissionBinding(for: tool)) {
                            ForEach(ToolPermissionLevel.allCases, id: \.self) { level in
                                Text(level.displayName).tag(level)
                            }
                        }
                        .pickerStyle(.menu)
                        .tint(ChatColors.accent)
                    }
                    .padding(10)
                    .background(ChatColors.background)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(ChatColors.border, lineWidth: 1)
                    )
                }
            }
        }
    }

    private var sessionSection: some View {
        SettingsSection(title: "Sesión", systemImage: "person.crop.circle") {
            Button {
                auth.logout()
            } label: {
                Label("Cerrar sesión", systemImage: "rectangle.portrait.and.arrow.right")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(SettingsButtonStyle(color: ChatColors.danger))
        }
    }

    private func saveConnection() {
        let cleanRelay = relayURL.trimmingCharacters(in: .whitespacesAndNewlines)
        let cleanIP = localIP.trimmingCharacters(in: .whitespacesAndNewlines)
        UserDefaults.standard.set(cleanRelay.isEmpty ? Constants.Relay.defaultURL : cleanRelay, forKey: Constants.Keys.relayURL)
        UserDefaults.standard.set(cleanIP.isEmpty ? Constants.Local.localIP : cleanIP, forKey: Constants.Keys.localIP)
        network.resolveMode()
    }

    private func permissionBinding(for tool: String) -> Binding<ToolPermissionLevel> {
        Binding(
            get: { permissions.permission(for: tool) },
            set: { permissions.setPermission($0, for: tool) }
        )
    }

    private func toolKind(_ tool: String) -> String {
        if MOBILE_BLOCKED_TOOLS.contains(tool) { return "Bloqueada por seguridad móvil" }
        if MOBILE_SAFE_TOOLS.contains(tool) { return "Segura para iOS" }
        return "Personalizada"
    }
}

private struct SettingsSection<Content: View>: View {
    let title: String
    let systemImage: String
    let content: () -> Content

    init(title: String, systemImage: String, @ViewBuilder content: @escaping () -> Content) {
        self.title = title
        self.systemImage = systemImage
        self.content = content
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: systemImage)
                    .foregroundStyle(ChatColors.accent)
                    .frame(width: 22)
                Text(title)
                    .font(.system(.headline, design: .rounded, weight: .semibold))
                    .foregroundStyle(ChatColors.textPrimary)
                Spacer()
            }

            content()
        }
        .padding(14)
        .background(ChatColors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(ChatColors.border, lineWidth: 1)
        )
    }
}

private struct SettingsTextField: View {
    let title: String
    @Binding var text: String
    let keyboard: UIKeyboardType

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title)
                .font(.system(.caption, design: .rounded, weight: .medium))
                .foregroundStyle(ChatColors.textSecondary)

            TextField(title, text: $text)
                .keyboardType(keyboard)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .font(.system(.subheadline, design: .monospaced))
                .foregroundStyle(ChatColors.textPrimary)
                .padding(.horizontal, 10)
                .padding(.vertical, 9)
                .background(ChatColors.background)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(ChatColors.border, lineWidth: 1)
                )
        }
    }
}

private struct SettingsButtonStyle: ButtonStyle {
    let color: Color

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(.subheadline, design: .rounded, weight: .semibold))
            .foregroundStyle(ChatColors.textPrimary)
            .padding(.vertical, 10)
            .background(color.opacity(configuration.isPressed ? 0.72 : 1.0))
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}

private extension ToolPermissionLevel {
    var displayName: String {
        switch self {
        case .auto: return "Auto"
        case .ask: return "Preguntar"
        case .block: return "Bloquear"
        }
    }
}

#Preview {
    NavigationStack {
        SettingsView()
    }
    .preferredColorScheme(.dark)
}
