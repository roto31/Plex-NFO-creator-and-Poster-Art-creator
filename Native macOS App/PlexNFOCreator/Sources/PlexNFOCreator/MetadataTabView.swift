import SwiftUI
import PlexNFOCore

struct MetadataTabView: View {
    @EnvironmentObject private var appState: AppState
    @State private var includeMusic = false
    @State private var forceRescan = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Metadata Generator").font(.title2)
            Text("Scans TV, movie, and optional music libraries for missing NFO files and artwork.")
                .foregroundStyle(.secondary)

            Toggle("Include music libraries", isOn: $includeMusic)
            Toggle("Force re-process existing items", isOn: $forceRescan)

            HStack {
                Button("Choose TV Library…") { pickLibrary(\.tvLibraryRoot) }
                Button("Choose Movies Library…") { pickLibrary(\.moviesLibraryRoot) }
                if includeMusic {
                    Button("Choose Music Library…") { pickLibrary(\.musicLibraryRoot) }
                }
            }

            librarySummary

            Button("Run Metadata Scan") { runScan() }
                .keyboardShortcut(.defaultAction)
                .disabled(appState.isJobRunning)
        }
        .padding()
        .onAppear {
            includeMusic = !appState.config.libraryPaths.musicLibraryRoot.isEmpty
                || !appState.config.libraryPaths.musicLibraryRoots.isEmpty
        }
    }

    private var librarySummary: some View {
        VStack(alignment: .leading, spacing: 4) {
            if !appState.config.libraryPaths.tvLibraryRoot.isEmpty {
                Text("TV: \(appState.config.libraryPaths.tvLibraryRoot)")
            }
            if !appState.config.libraryPaths.moviesLibraryRoot.isEmpty {
                Text("Movies: \(appState.config.libraryPaths.moviesLibraryRoot)")
            }
            if includeMusic, !appState.config.libraryPaths.musicLibraryRoot.isEmpty {
                Text("Music: \(appState.config.libraryPaths.musicLibraryRoot)")
            }
        }
        .font(.callout)
        .foregroundStyle(.secondary)
    }

    private func pickLibrary(_ keyPath: WritableKeyPath<LibraryPathsConfig, String>) {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            appState.config.libraryPaths[keyPath: keyPath] = url.path
            appState.saveConfig()
        }
    }

    private func runScan() {
        let options = MetadataGeneratorOptions(
            includeMusic: includeMusic,
            force: forceRescan,
            dryRun: appState.config.dryRunByDefault
        )
        let request = MetadataGeneratorRequest(
            options: options,
            config: appState.config,
            settings: appState.config.metadataSettings
        )
        let service = MetadataGeneratorService(keychain: appState.keychain, logging: appState.logging)
        appState.runJob(kind: .metadata) {
            let reporter = MetadataProgressReporter(
                onLog: { message in
                    Task { @MainActor in appState.jobLog.append(message) }
                },
                onProgress: { current, total, path in
                    Task { @MainActor in
                        appState.jobLog.append("[\(current)/\(total)] \(path)")
                    }
                }
            )
            let summary = try await service.run(request: request, reporter: reporter)
            return summary.description
        }
    }
}
