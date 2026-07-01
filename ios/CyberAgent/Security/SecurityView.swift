import SwiftUI

/// SEC-012 / I-01: Sección "Seguridad" del módulo iOS.
/// Visible pero DESACTIVADA (apartados conectados, sin funcionalidad todavía),
/// con el estilo CyberAgent. Espeja la vista Seguridad de la web (cámaras,
/// eventos, alertas, autonomía, apps). Se activará cuando el backend de
/// seguridad esté operativo (SECURITY_ENABLED).
struct SecurityView: View {
    private let sections: [SecuritySection] = [
        .init(icon: "video.fill", title: "Cámaras",
              subtitle: "Vigilancia exterior e interior en tiempo real"),
        .init(icon: "bell.badge.fill", title: "Alertas",
              subtitle: "Historial de amenazas y avisos"),
        .init(icon: "clock.arrow.circlepath", title: "Eventos",
              subtitle: "Línea de tiempo de actividad"),
        .init(icon: "brain.head.profile", title: "Autonomía",
              subtitle: "Manual · operativa · alto impacto"),
        .init(icon: "pawprint.fill", title: "Mascotas",
              subtitle: "Reconocimiento y patrones de los gatos"),
        .init(icon: "speaker.wave.3.fill", title: "Disuasión",
              subtitle: "Actuadores: altavoz, luces, narración")
    ]

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                header
                ForEach(sections) { section in
                    SecurityCard(section: section)
                }
                Text("El módulo de seguridad se activará próximamente.")
                    .font(CAFont.caption)
                    .foregroundStyle(CAColors.textSecondary)
                    .padding(.top, 8)
            }
            .padding(16)
        }
        .background(CAColors.backgroundPrimary.ignoresSafeArea())
        .navigationTitle("Seguridad")
    }

    private var header: some View {
        HStack(spacing: 12) {
            Image(systemName: "shield.lefthalf.filled")
                .font(.system(size: 28))
                .foregroundStyle(CAColors.accent)
            VStack(alignment: .leading, spacing: 2) {
                Text("Centro de seguridad")
                    .font(CAFont.headline)
                    .foregroundStyle(CAColors.textPrimary)
                Text("Cámaras · Home Assistant · IA de vigilancia")
                    .font(CAFont.caption)
                    .foregroundStyle(CAColors.textSecondary)
            }
            Spacer()
            StatusPill(text: "Desactivado", color: CAColors.textSecondary)
        }
        .padding(14)
        .background(CAColors.backgroundSecondary)
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }
}

private struct SecuritySection: Identifiable {
    let id = UUID()
    let icon: String
    let title: String
    let subtitle: String
}

private struct SecurityCard: View {
    let section: SecuritySection

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: section.icon)
                .font(.system(size: 20))
                .foregroundStyle(CAColors.accent)
                .frame(width: 32)
            VStack(alignment: .leading, spacing: 3) {
                Text(section.title)
                    .font(CAFont.bodyMedium)
                    .foregroundStyle(CAColors.textPrimary)
                Text(section.subtitle)
                    .font(CAFont.caption)
                    .foregroundStyle(CAColors.textSecondary)
            }
            Spacer()
            Text("próximamente")
                .font(CAFont.captionMedium)
                .foregroundStyle(CAColors.textSecondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(CAColors.backgroundPrimary)
                .clipShape(Capsule())
        }
        .padding(14)
        .background(CAColors.backgroundSecondary)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(CAColors.borderColor, lineWidth: 1)
        )
        .opacity(0.85)
    }
}

private struct StatusPill: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(CAFont.captionMedium)
            .foregroundStyle(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(CAColors.backgroundPrimary)
            .clipShape(Capsule())
    }
}

#Preview {
    NavigationStack {
        SecurityView()
    }
    .preferredColorScheme(.dark)
}
