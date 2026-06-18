import SwiftUI
import PlexNFOCore

struct RenameTabView: View {
    @EnvironmentObject private var appState: AppState
    @State private var rootPath = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Rename Movies").font(.title2)
            HStack {
                TextField("Movies library root", text: $rootPath)
                Button("Browse…") { pickFolder() }
            }
            Button("Preview Rename") {
                let url = URL(fileURLWithPath: rootPath)
                appState.runJob(kind: .rename) {
                    let items = RenameService().preview(root: url, dryRun: true)
                    return items.map { "\($0.originalPath) → \($0.proposedPath)" }.joined(separator: "\n")
                }
            }
            .disabled(rootPath.isEmpty)
        }
        .padding()
        .onAppear {
            rootPath = appState.config.libraryPaths.moviesLibraryRoot
        }
    }

    private func pickFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        if panel.runModal() == .OK, let url = panel.url {
            rootPath = url.path
        }
    }
}
