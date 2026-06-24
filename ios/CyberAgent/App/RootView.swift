import SwiftUI

struct RootView: View {
    @StateObject private var chatViewModel = ChatViewModel()

    var body: some View {
        TabView {
            NavigationStack {
                PlaceholderPanel(
                    title: "Chat",
                    subtitle: chatViewModel.connectionStatus,
                    systemImage: "message",
                    accent: AppChrome.accent
                )
            }
            .tabItem {
                Label("Chat", systemImage: "message")
            }

            NavigationStack {
                PlaceholderPanel(
                    title: "Dispositivos",
                    subtitle: "BLE, GPS y accesorios",
                    systemImage: "bolt.horizontal",
                    accent: AppChrome.success
                )
            }
            .tabItem {
                Label("Dispositivos", systemImage: "bolt.horizontal")
            }

            NavigationStack {
                PlaceholderPanel(
                    title: "Ajustes",
                    subtitle: "Relay, red local y permisos",
                    systemImage: "gear",
                    accent: AppChrome.secondaryText
                )
            }
            .tabItem {
                Label("Ajustes", systemImage: "gear")
            }
        }
        .tint(AppChrome.accent)
        .toolbarBackground(AppChrome.backgroundSecondary, for: .tabBar)
        .toolbarBackground(.visible, for: .tabBar)
        .background(AppChrome.backgroundPrimary.ignoresSafeArea())
    }
}

private enum AppChrome {
    static let backgroundPrimary = Color(red: 13 / 255, green: 17 / 255, blue: 23 / 255)
    static let backgroundSecondary = Color(red: 22 / 255, green: 27 / 255, blue: 34 / 255)
    static let border = Color(red: 48 / 255, green: 54 / 255, blue: 61 / 255)
    static let accent = Color(red: 88 / 255, green: 166 / 255, blue: 255 / 255)
    static let success = Color(red: 63 / 255, green: 185 / 255, blue: 80 / 255)
    static let primaryText = Color.white
    static let secondaryText = Color(red: 139 / 255, green: 148 / 255, blue: 158 / 255)
}

private struct PlaceholderPanel: View {
    let title: String
    let subtitle: String
    let systemImage: String
    let accent: Color

    var body: some View {
        ZStack {
            AppChrome.backgroundPrimary.ignoresSafeArea()

            VStack(spacing: 16) {
                Image(systemName: systemImage)
                    .font(.system(size: 34, weight: .semibold))
                    .foregroundStyle(accent)
                    .frame(width: 64, height: 64)
                    .background(AppChrome.backgroundSecondary)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(AppChrome.border, lineWidth: 1)
                    )

                VStack(spacing: 6) {
                    Text(title)
                        .font(.system(.title3, design: .rounded, weight: .semibold))
                        .foregroundStyle(AppChrome.primaryText)

                    Text(subtitle)
                        .font(.system(.subheadline, design: .rounded))
                        .foregroundStyle(AppChrome.secondaryText)
                        .multilineTextAlignment(.center)
                }
            }
            .padding(24)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(AppChrome.backgroundPrimary, for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
    }
}

#Preview {
    RootView()
        .preferredColorScheme(.dark)
}
