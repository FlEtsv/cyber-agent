import SwiftUI

struct RootView: View {
    @StateObject private var chatViewModel = ChatViewModel()

    var body: some View {
        TabView {
            NavigationStack {
                ChatView(viewModel: chatViewModel)
            }
            .tabItem {
                Label("Chat", systemImage: "message")
            }

            NavigationStack {
                DevicesView()
            }
            .tabItem {
                Label("Dispositivos", systemImage: "bolt.horizontal")
            }

            NavigationStack {
                SettingsView()
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
    static let accent = Color(red: 88 / 255, green: 166 / 255, blue: 255 / 255)
}

#Preview {
    RootView()
        .preferredColorScheme(.dark)
}
