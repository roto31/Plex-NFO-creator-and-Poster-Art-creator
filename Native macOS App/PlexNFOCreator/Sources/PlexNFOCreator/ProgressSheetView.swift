import SwiftUI
import AppKit

struct ProgressSheetView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Job Progress")
                    .font(.headline)
                Spacer()
                if appState.isJobRunning {
                    ProgressView()
                        .controlSize(.small)
                }
            }
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 4) {
                    ForEach(Array(appState.jobLog.enumerated()), id: \.offset) { _, line in
                        Text(line)
                            .font(.system(.body, design: .monospaced))
                            .textSelection(.enabled)
                    }
                }
            }
            HStack {
                Button("Open Console") {
                    NSWorkspace.shared.open(URL(fileURLWithPath: "/System/Applications/Utilities/Console.app"))
                }
                Spacer()
                Button("Cancel") {
                    Task { await appState.cancelJob() }
                }
                .disabled(!appState.isJobRunning)
                Button("Close") { dismiss() }
                    .disabled(appState.isJobRunning)
            }
        }
        .padding()
        .frame(width: 560, height: 360)
    }
}
