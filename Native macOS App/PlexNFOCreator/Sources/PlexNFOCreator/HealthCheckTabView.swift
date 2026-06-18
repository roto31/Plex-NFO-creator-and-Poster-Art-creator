import SwiftUI
import PlexNFOCore

struct HealthCheckTabView: View {
    @EnvironmentObject private var appState: AppState
    @State private var results: [HealthCheckResult.Check] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Health Check").font(.title2)
            Text("Runs configuration, connectivity, scheduling, and disk space diagnostics.")
                .foregroundStyle(.secondary)

            Button("Run Health Check") { runHealthCheck() }
                .disabled(appState.isJobRunning)

            if !results.isEmpty {
                List(results, id: \.name) { check in
                    HStack(alignment: .top) {
                        Text(check.passed ? "✅" : "⚠️")
                        VStack(alignment: .leading) {
                            Text(check.name).font(.headline)
                            Text(check.detail).font(.callout).foregroundStyle(.secondary)
                        }
                    }
                }
                .frame(minHeight: 200)
            }
        }
        .padding()
    }

    private func runHealthCheck() {
        let config = appState.config
        let keychain = appState.keychain
        appState.runJob(kind: .health) {
            let service = HealthCheckService(config: config, keychain: keychain)
            let result = await service.run()
            await MainActor.run { results = result.checks }
            let summary = result.checks.map { "\($0.passed ? "PASS" : "WARN") \($0.name): \($0.detail)" }
            return summary.joined(separator: "\n")
        }
    }
}
