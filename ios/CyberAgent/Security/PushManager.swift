// I-02: PushManager — recibir alertas de seguridad vía notificaciones push iOS
// Requiere: UNUserNotificationCenter + APNs/FCM token enviado al backend CyberAgent

import Foundation
import UserNotifications
import UIKit

// MARK: - PushManager

final class PushManager: NSObject, ObservableObject {

    static let shared = PushManager()

    @Published var isRegistered = false
    @Published var lastAlert: PushAlert? = nil

    private var deviceToken: String? = nil

    // MARK: - Registro

    func requestPermission() {
        UNUserNotificationCenter.current().requestAuthorization(
            options: [.alert, .badge, .sound]
        ) { granted, error in
            DispatchQueue.main.async {
                if granted {
                    UIApplication.shared.registerForRemoteNotifications()
                }
                if let error = error {
                    print("[PushManager] permiso denegado: \(error.localizedDescription)")
                }
            }
        }
    }

    func didRegisterForRemoteNotifications(deviceToken: Data) {
        let tokenString = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        self.deviceToken = tokenString
        isRegistered = true
        print("[PushManager] token: \(tokenString)")
        sendTokenToBackend(token: tokenString)
    }

    func didFailToRegisterForRemoteNotifications(error: Error) {
        print("[PushManager] registro fallido: \(error.localizedDescription)")
        isRegistered = false
    }

    // MARK: - Procesamiento de notificación entrante

    func handleRemoteNotification(userInfo: [AnyHashable: Any]) {
        guard let aps = userInfo["aps"] as? [String: Any] else { return }
        let alert = PushAlert(
            title: (aps["alert"] as? [String: String])?["title"] ?? "CyberAgent",
            body: (aps["alert"] as? [String: String])?["body"] ?? "",
            severity: userInfo["severity"] as? String ?? "media",
            cam_id: userInfo["cam_id"] as? String,
            ts: Date()
        )
        DispatchQueue.main.async {
            self.lastAlert = alert
        }
        // Si la app está en background, la notificación del sistema ya se mostró.
        // Si está en foreground, podemos mostrar un banner custom.
        if UIApplication.shared.applicationState == .active {
            showInAppBanner(alert: alert)
        }
    }

    // MARK: - Comunicación con backend

    private func sendTokenToBackend(token: String) {
        guard let url = URL(string: "\(Constants.baseURL)/api/push/register") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ["device_token": token, "platform": "ios"]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { _, response, error in
            if let error = error {
                print("[PushManager] error registrando token: \(error)")
            } else {
                print("[PushManager] token enviado al backend")
            }
        }.resume()
    }

    // MARK: - Banner in-app

    private func showInAppBanner(alert: PushAlert) {
        // Usar notificación local para mostrar banner en primer plano
        let content = UNMutableNotificationContent()
        content.title = alert.title
        content.body = alert.body
        content.sound = alert.severity == "critica" ? .defaultCritical : .default
        if let camId = alert.cam_id {
            content.userInfo = ["cam_id": camId]
        }
        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil
        )
        UNUserNotificationCenter.current().add(request)
    }
}

// MARK: - UNUserNotificationCenterDelegate

extension PushManager: UNUserNotificationCenterDelegate {
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        // Mostrar banner incluso en foreground
        completionHandler([.banner, .sound, .badge])
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        let info = response.notification.request.content.userInfo
        if let camId = info["cam_id"] as? String {
            // Navegar a la vista de la cámara
            NotificationCenter.default.post(
                name: .openCameraView,
                object: nil,
                userInfo: ["cam_id": camId]
            )
        }
        completionHandler()
    }
}

// MARK: - Modelos

struct PushAlert: Identifiable {
    let id = UUID()
    var title: String
    var body: String
    var severity: String
    var cam_id: String?
    var ts: Date
}

extension Notification.Name {
    static let openCameraView = Notification.Name("openCameraView")
}
