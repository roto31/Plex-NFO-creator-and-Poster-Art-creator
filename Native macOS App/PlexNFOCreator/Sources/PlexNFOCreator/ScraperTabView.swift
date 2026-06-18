import SwiftUI
import PlexNFOCore

struct ScraperTabView: View {
    @EnvironmentObject private var appState: AppState
    @State private var title = "Inception"
    @State private var year = "2010"

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("NFO Scraper").font(.title2)
            TextField("Title", text: $title)
            TextField("Year", text: $year)
            Button("Generate NFO") {
                appState.runJob(kind: .scraper) {
                    let tmdb = (try? appState.keychain.get(.tmdbAPIKey)) ?? ""
                    let tvdb = (try? appState.keychain.get(.tvdbAPIKey)) ?? ""
                    let service = ScraperService(tmdbAPIKey: tmdb, tvdbAPIKey: tvdb)
                    return try await service.generateMovieNFO(title: title, year: year)
                }
            }
        }
        .padding()
    }
}
