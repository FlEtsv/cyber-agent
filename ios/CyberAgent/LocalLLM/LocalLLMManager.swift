import Foundation
import CoreML

// Wrapper for on-device inference. The actual .mlpackage is added in Xcode
// by dragging a CoreML model (e.g. llama.cpp → exportCoreML, or mlx-lm convert).
// Name the model target "CyberAgentMini" in the Xcode project.
//
// If the model is not present, falls back to a minimal echo / rule-based response.

enum LocalLLMError: Error {
    case modelNotFound
    case inferenceError(String)
}

struct LocalLLMResponse {
    let text: String
    let usedLocalModel: Bool
    let toolCalls: [String]
}

@MainActor
final class LocalLLMManager: ObservableObject {
    static let shared = LocalLLMManager()

    @Published var isAvailable  = false
    @Published var isProcessing = false

    private var model: MLModel?
    private let safeTools = MOBILE_SAFE_TOOLS

    private init() {
        Task { await loadModel() }
    }

    func generate(prompt: String, history: [[String: String]]) async throws -> LocalLLMResponse {
        isProcessing = true
        defer { isProcessing = false }

        guard model != nil else {
            return try await ruleBasedFallback(prompt: prompt)
        }
        return try await coreMLInference(prompt: prompt, history: history)
    }

    // MARK: - CoreML Inference

    private func coreMLInference(prompt: String, history: [[String: String]]) async throws -> LocalLLMResponse {
        guard let model else { throw LocalLLMError.modelNotFound }

        let inputText = buildContextString(history: history, currentPrompt: prompt)
        let inputFeature = try MLDictionaryFeatureProvider(
            dictionary: ["text": inputText as NSString]
        )
        let result     = try model.prediction(from: inputFeature)
        let outputText = result.featureValue(for: "output")?.stringValue ?? ""

        let toolCalls = extractToolCalls(from: outputText)
        let filteredTools = toolCalls.filter { safeTools.contains($0) }

        return LocalLLMResponse(text: cleanOutput(outputText),
                                usedLocalModel: true,
                                toolCalls: filteredTools)
    }

    // MARK: - Rule-based fallback (no model loaded)

    private func ruleBasedFallback(prompt: String) async throws -> LocalLLMResponse {
        let lower = prompt.lowercased()
        let response: String

        if lower.contains("gps") || lower.contains("ubicaci") || lower.contains("donde") {
            let summary = GPSManager.shared.currentLocationSummary()
            if let lat = summary["latitude"] as? Double, let lon = summary["longitude"] as? Double {
                response = "Tu ubicación actual: \(String(format: "%.5f", lat)), \(String(format: "%.5f", lon)). \(summary["address"] as? String ?? "")"
            } else {
                response = "GPS no disponible. Activa la ubicación en Ajustes."
            }
        } else if lower.contains("bluetooth") || lower.contains("ble") || lower.contains("dispositivo") {
            let ble = BLEManager.shared
            if ble.discoveredDevices.isEmpty {
                response = "No hay dispositivos Bluetooth detectados. Inicia un escaneo desde la pestaña Dispositivos."
            } else {
                let names = ble.discoveredDevices.map { $0.displayName }.joined(separator: ", ")
                response = "Dispositivos BLE detectados (\(ble.discoveredDevices.count)): \(names)"
            }
        } else if lower.contains("sin internet") || lower.contains("offline") || lower.contains("local") {
            response = "Estoy en modo local. Puedo responder preguntas básicas y acceder a GPS/Bluetooth. Para operaciones avanzadas necesito conexión al relay."
        } else if lower.contains("hola") || lower.contains("ayuda") {
            response = "¡Hola! Soy CyberAgent en modo local. Puedo consultar tu GPS, dispositivos Bluetooth y accesorios conectados. Para comandos avanzados necesito conexión al PC."
        } else {
            response = "Procesando en modo local. Para esta tarea necesito conexión al relay/PC. ¿Tienes internet disponible?"
        }

        return LocalLLMResponse(text: response, usedLocalModel: false, toolCalls: [])
    }

    // MARK: - Helpers

    private func loadModel() async {
        guard let modelURL = Bundle.main.url(forResource: "CyberAgentMini", withExtension: "mlmodelc") else {
            isAvailable = false
            return
        }
        do {
            model = try MLModel(contentsOf: modelURL)
            isAvailable = true
        } catch {
            isAvailable = false
        }
    }

    private func buildContextString(history: [[String: String]], currentPrompt: String) -> String {
        var ctx = "[INSTRUCCION] Eres CyberAgent, asistente de ciberseguridad en iPhone. "
            + "Acceso a GPS, Bluetooth y accesorios USB. Solo tareas seguras y rápidas.\n"
        for turn in history.suffix(6) {
            let role = turn["role"] ?? "user"
            let content = turn["content"] ?? ""
            ctx += "[\(role.uppercased())] \(content)\n"
        }
        ctx += "[USER] \(currentPrompt)\n[ASSISTANT]"
        return ctx
    }

    private func extractToolCalls(from text: String) -> [String] {
        let pattern = #"<tool:(\w+)>"#
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return [] }
        let range = NSRange(text.startIndex..., in: text)
        return regex.matches(in: text, range: range).compactMap {
            Range($0.range(at: 1), in: text).map { String(text[$0]) }
        }
    }

    private func cleanOutput(_ text: String) -> String {
        text.replacingOccurrences(of: #"<tool:\w+>"#, with: "", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
