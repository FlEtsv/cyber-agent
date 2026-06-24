import SwiftUI

@main
struct CyberAgentApp: App {
    @StateObject private var auth    = AuthManager.shared
    @StateObject private var network = NetworkMonitor.shared
    @StateObject private var ble     = BLEManager.shared
    @StateObject private var gps     = GPSManager.shared

    var body: some Scene {
        WindowGroup {
            if auth.isAuthenticated {
                RootView()
                    .environmentObject(auth)
                    .environmentObject(network)
                    .environmentObject(ble)
                    .environmentObject(gps)
                    .preferredColorScheme(.dark)
            } else {
                LoginView()
                    .environmentObject(auth)
                    .environmentObject(network)
                    .preferredColorScheme(.dark)
            }
        }
    }
}
