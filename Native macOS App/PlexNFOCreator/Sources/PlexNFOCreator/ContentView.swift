import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        TabView {
            RenameTabView()
                .tabItem { Label("Rename", systemImage: "textformat") }
            ScraperTabView()
                .tabItem { Label("Scraper", systemImage: "doc.text.magnifyingglass") }
            ArtworkTabView()
                .tabItem { Label("Artwork", systemImage: "photo") }
            MetadataTabView()
                .tabItem { Label("Metadata", systemImage: "sparkles.rectangle.stack") }
            HealthCheckTabView()
                .tabItem { Label("Health", systemImage: "heart.text.square") }
        }
        .frame(minWidth: 900, minHeight: 600)
        .sheet(isPresented: $appState.showProgressSheet) {
            ProgressSheetView()
                .environmentObject(appState)
        }
        .toolbar {
            ToolbarItem(placement: .automatic) {
                Button("About") {
                    NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
                }
            }
        }
    }
}
