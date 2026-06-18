import SwiftUI
import PlexNFOCore

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var tmdbKey = ""
    @State private var tvdbKey = ""
    @State private var plexToken = ""
    @State private var fanartKey = ""
    @State private var schedulingMessage = ""

    var body: some View {
        Form {
            Section("API Keys") {
                SecureField("TMDB API Key", text: $tmdbKey)
                SecureField("TVDB API Key", text: $tvdbKey)
                SecureField("Plex Token", text: $plexToken)
                SecureField("FanArt.tv API Key", text: $fanartKey)
                Button("Save Keys") { saveKeys() }
            }
            Section("Library Paths") {
                TextField("Movies root", text: $appState.config.libraryPaths.moviesLibraryRoot)
                TextField("TV root", text: $appState.config.libraryPaths.tvLibraryRoot)
                TextField("Music root", text: $appState.config.libraryPaths.musicLibraryRoot)
                Button("Save Settings") { appState.saveConfig() }
            }
            Section("Metadata Generator") {
                TextField("Tunarr DB path", text: $appState.config.metadataSettings.tunarrDBPath)
                TextField("Cache directory", text: $appState.config.metadataSettings.cacheDirectory)
                TextField("Plex TV library key", text: $appState.config.metadataSettings.plexTVLibraryKey)
                TextField("Plex Movies library key", text: $appState.config.metadataSettings.plexMoviesLibraryKey)
                TextField("Plex Music library key", text: $appState.config.metadataSettings.plexMusicLibraryKey)
                TextField("MusicBrainz contact email", text: $appState.config.metadataSettings.musicBrainzContact)
                Toggle("Subtitles enabled", isOn: $appState.config.metadataSettings.subtitlesEnabled)
            }
            Section("Daily Scheduling") {
                Toggle("Enable daily metadata scan", isOn: $appState.config.metadataSettings.scheduling.enabled)
                Stepper(
                    "Run at \(String(format: "%02d:%02d", appState.config.metadataSettings.scheduling.hour, appState.config.metadataSettings.scheduling.minute))",
                    value: $appState.config.metadataSettings.scheduling.hour,
                    in: 0...23
                )
                Stepper("Minute", value: $appState.config.metadataSettings.scheduling.minute, in: 0...59)
                Button("Apply Scheduling") { applyScheduling() }
                if !schedulingMessage.isEmpty {
                    Text(schedulingMessage).font(.callout).foregroundStyle(.secondary)
                }
            }
            Section("Defaults") {
                Toggle("Dry run by default", isOn: $appState.config.dryRunByDefault)
            }
            Section("About") {
                AboutView()
            }
        }
        .padding()
        .frame(width: 520)
        .onAppear(perform: loadKeys)
    }

    private func loadKeys() {
        tmdbKey = (try? appState.keychain.get(.tmdbAPIKey)) ?? ""
        tvdbKey = (try? appState.keychain.get(.tvdbAPIKey)) ?? ""
        plexToken = (try? appState.keychain.get(.plexToken)) ?? ""
        fanartKey = (try? appState.keychain.get(.fanartAPIKey)) ?? ""
    }

    private func saveKeys() {
        try? appState.keychain.set(tmdbKey, for: .tmdbAPIKey)
        try? appState.keychain.set(tvdbKey, for: .tvdbAPIKey)
        try? appState.keychain.set(plexToken, for: .plexToken)
        try? appState.keychain.set(fanartKey, for: .fanartAPIKey)
        appState.saveConfig()
    }

    private func applyScheduling() {
        appState.saveConfig()
        let executable = Bundle.main.bundlePath + "/Contents/MacOS/PlexNFOCreator"
        do {
            schedulingMessage = try DailySchedulingManager.apply(
                enabled: appState.config.metadataSettings.scheduling.enabled,
                schedule: appState.config.metadataSettings.scheduling,
                executablePath: executable
            )
        } catch {
            schedulingMessage = "Scheduling error: \(error.localizedDescription)"
        }
    }
}
