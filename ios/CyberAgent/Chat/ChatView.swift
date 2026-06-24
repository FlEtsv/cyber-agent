import SwiftUI

struct ChatView: View {
    @ObservedObject var viewModel: ChatViewModel
    @FocusState private var inputFocused: Bool

    var body: some View {
        ZStack(alignment: .bottom) {
            ChatColors.background.ignoresSafeArea()

            VStack(spacing: 0) {
                statusBar

                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(viewModel.messages) { message in
                                MessageBubble(message: message)
                                    .id(message.id)
                            }

                            if viewModel.isThinking {
                                TypingIndicator()
                                    .id("typing")
                            }
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 16)
                    }
                    .scrollDismissesKeyboard(.interactively)
                    .onChange(of: viewModel.messages.count) { _, _ in
                        scrollToBottom(proxy)
                    }
                    .onChange(of: viewModel.isThinking) { _, _ in
                        scrollToBottom(proxy)
                    }
                }

                inputBar
            }

            if !viewModel.pendingApprovals.isEmpty {
                approvalOverlay
            }
        }
        .navigationTitle("Chat")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    viewModel.clearHistory()
                } label: {
                    Image(systemName: "trash")
                }
                .tint(ChatColors.textSecondary)
                .accessibilityLabel("Limpiar historial")
            }
        }
    }

    private var statusBar: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(statusColor)
                .frame(width: 8, height: 8)

            Text(viewModel.connectionStatus)
                .font(.system(.caption, design: .rounded, weight: .medium))
                .foregroundStyle(ChatColors.textSecondary)

            Spacer()

            if let error = viewModel.errorBanner {
                Text(error)
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(ChatColors.danger)
                    .lineLimit(1)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(ChatColors.surface)
        .overlay(Rectangle().fill(ChatColors.border).frame(height: 1), alignment: .bottom)
    }

    private var inputBar: some View {
        HStack(alignment: .bottom, spacing: 10) {
            TextField("Mensaje", text: $viewModel.inputText, axis: .vertical)
                .lineLimit(1...5)
                .focused($inputFocused)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .foregroundStyle(ChatColors.textPrimary)
                .background(ChatColors.surface)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(inputFocused ? ChatColors.accent : ChatColors.border, lineWidth: 1)
                )
                .submitLabel(.send)
                .onSubmit(send)

            Button {
                if viewModel.isThinking {
                    viewModel.stopAgent()
                } else {
                    send()
                }
            } label: {
                Image(systemName: viewModel.isThinking ? "stop.fill" : "arrow.up")
                    .font(.system(size: 16, weight: .bold))
                    .frame(width: 38, height: 38)
                    .foregroundStyle(ChatColors.textPrimary)
                    .background(sendButtonColor)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
            .disabled(!viewModel.isThinking && viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .accessibilityLabel(viewModel.isThinking ? "Detener agente" : "Enviar mensaje")
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .background(ChatColors.background)
        .overlay(Rectangle().fill(ChatColors.border).frame(height: 1), alignment: .top)
    }

    private var approvalOverlay: some View {
        VStack {
            Spacer()
            VStack(spacing: 10) {
                ForEach(viewModel.pendingApprovals) { payload in
                    ToolApprovalCard(
                        payload: payload,
                        approve: { viewModel.approve(toolId: payload.id) },
                        reject: { viewModel.reject(toolId: payload.id) }
                    )
                }
            }
            .padding(14)
            .padding(.bottom, 62)
        }
        .background(Color.black.opacity(0.22).ignoresSafeArea())
    }

    private var statusColor: Color {
        viewModel.connectionStatus.lowercased().contains("desconect")
            ? ChatColors.danger
            : ChatColors.success
    }

    private var sendButtonColor: Color {
        viewModel.isThinking ? ChatColors.danger : ChatColors.accent
    }

    private func send() {
        viewModel.sendMessage()
    }

    private func scrollToBottom(_ proxy: ScrollViewProxy) {
        withAnimation(.easeOut(duration: 0.2)) {
            if let last = viewModel.messages.last {
                proxy.scrollTo(last.id, anchor: .bottom)
            } else if viewModel.isThinking {
                proxy.scrollTo("typing", anchor: .bottom)
            }
        }
    }
}

private struct TypingIndicator: View {
    var body: some View {
        HStack {
            HStack(spacing: 6) {
                ProgressView()
                    .controlSize(.small)
                    .tint(ChatColors.accent)
                Text("Pensando")
                    .font(.system(.caption, design: .rounded, weight: .medium))
                    .foregroundStyle(ChatColors.textSecondary)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 9)
            .background(ChatColors.surface)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(ChatColors.border, lineWidth: 1)
            )
            Spacer(minLength: 48)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

#Preview {
    NavigationStack {
        ChatView(viewModel: ChatViewModel())
    }
    .preferredColorScheme(.dark)
}
