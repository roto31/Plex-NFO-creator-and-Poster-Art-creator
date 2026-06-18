import SwiftUI
import PlexNFOCore

struct FirstLaunchWizardView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Welcome to Plex NFO Creator")
                .font(.title2)
            Text("Configure library paths and API keys to get started. Keys are stored in the Keychain.")
            Button("Run Preflight") {
                let preflight = PreflightService(keychain: appState.keychain)
                let result = preflight.run(configStore: appState.configStore)
                appState.jobLog = result.messages
                appState.showProgressSheet = true
            }
            HStack {
                Spacer()
                Button("Skip") {
                    appState.config.firstLaunchCompleted = true
                    appState.saveConfig()
                    dismiss()
                }
                Button("Continue") {
                    appState.config.firstLaunchCompleted = true
                    appState.saveConfig()
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(24)
        .frame(width: 480)
    }
}
