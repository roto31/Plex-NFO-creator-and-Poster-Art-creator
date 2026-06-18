import SwiftUI

struct AboutView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Plex NFO Creator")
                .font(.title)
            Text(appState.versionInfo.displayString)
                .font(.headline)
            Text("Native macOS app for NFO generation, artwork extraction, and library maintenance.")
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding(24)
        .frame(width: 420, height: 200)
    }
}
