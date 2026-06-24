import SwiftUI

struct LoginView: View {
    @StateObject private var auth = AuthManager.shared

    @State private var email    = ""
    @State private var password = ""
    @State private var totp     = ""
    @State private var showTotp = false

    var body: some View {
        ZStack {
            Color(hex: "#0d1117").ignoresSafeArea()

            VStack(spacing: 32) {
                Spacer()

                VStack(spacing: 8) {
                    Image(systemName: "shield.lefthalf.filled")
                        .font(.system(size: 56, weight: .light))
                        .foregroundColor(Color(hex: "#58a6ff"))

                    Text("CyberAgent")
                        .font(.system(size: 28, weight: .semibold, design: .monospaced))
                        .foregroundColor(.white)

                    Text("Agente de ciberseguridad")
                        .font(.subheadline)
                        .foregroundColor(Color(hex: "#8b949e"))
                }

                VStack(spacing: 16) {
                    CATextField(placeholder: "Email", text: $email)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()

                    CASecureField(placeholder: "Contraseña", text: $password)

                    if auth.totpRequired || showTotp {
                        CATextField(placeholder: "Código TOTP (6 dígitos)", text: $totp)
                            .keyboardType(.numberPad)
                    }
                }
                .padding(.horizontal, 24)

                if let err = auth.errorMessage {
                    Text(err)
                        .font(.caption)
                        .foregroundColor(Color(hex: "#f85149"))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                }

                Button(action: handleLogin) {
                    Group {
                        if auth.isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        } else {
                            Text("Iniciar sesión")
                                .font(.system(size: 16, weight: .semibold))
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .background(Color(hex: "#238636"))
                    .foregroundColor(.white)
                    .cornerRadius(10)
                }
                .padding(.horizontal, 24)
                .disabled(auth.isLoading || email.isEmpty || password.isEmpty)

                Spacer()

                ConnectionStatusBar()
            }
        }
        .task { await auth.checkStatus() }
        .onChange(of: auth.totpRequired) { _, required in
            showTotp = required
        }
    }

    private func handleLogin() {
        Task {
            _ = await auth.login(email: email, password: password, totp: totp)
        }
    }
}

// MARK: - Reusable components

struct CATextField: View {
    let placeholder: String
    @Binding var text: String

    var body: some View {
        TextField(placeholder, text: $text)
            .padding(12)
            .background(Color(hex: "#161b22"))
            .foregroundColor(.white)
            .cornerRadius(8)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(hex: "#30363d"), lineWidth: 1))
            .accentColor(Color(hex: "#58a6ff"))
    }
}

struct CASecureField: View {
    let placeholder: String
    @Binding var text: String

    var body: some View {
        SecureField(placeholder, text: $text)
            .padding(12)
            .background(Color(hex: "#161b22"))
            .foregroundColor(.white)
            .cornerRadius(8)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(hex: "#30363d"), lineWidth: 1))
            .accentColor(Color(hex: "#58a6ff"))
    }
}

struct ConnectionStatusBar: View {
    @ObservedObject private var monitor = NetworkMonitor.shared

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(monitor.isOnline ? Color(hex: "#3fb950") : Color(hex: "#f85149"))
                .frame(width: 8, height: 8)
            Text(monitor.isOnline ? "Relay en línea" : "Modo local")
                .font(.caption2)
                .foregroundColor(Color(hex: "#8b949e"))
        }
        .padding(.bottom, 16)
    }
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xFF) / 255
        let g = Double((int >> 8)  & 0xFF) / 255
        let b = Double(int         & 0xFF) / 255
        self.init(red: r, green: g, blue: b)
    }
}
