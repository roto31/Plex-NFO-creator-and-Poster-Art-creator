import SwiftUI
import PlexNFOCore

struct ArtworkTabView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Artwork Extraction").font(.title2)
            Text(FFmpegLocator.isAvailable() ? "ffmpeg found" : "ffmpeg not found (bundle in future release)")
                .foregroundStyle(FFmpegLocator.isAvailable() ? .green : .orange)
            Button("Check FFmpeg") {
                appState.runJob(kind: .artwork) {
                    if let url = FFmpegLocator.locate() {
                        return "Using ffmpeg at \(url.path)"
                    }
                    return "ffmpeg not available"
                }
            }
        }
        .padding()
    }
}
