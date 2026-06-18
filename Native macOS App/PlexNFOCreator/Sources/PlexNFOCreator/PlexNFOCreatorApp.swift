import SwiftUI

@main
struct PlexNFOCreatorApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .sheet(isPresented: $appState.showFirstLaunch) {
                    FirstLaunchWizardView()
                        .environmentObject(appState)
                }
        }
        Settings {
            SettingsView()
                .environmentObject(appState)
        }
    }
}
