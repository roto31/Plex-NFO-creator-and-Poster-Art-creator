import XCTest
@testable import PlexNFOCore

final class ConfigStoreTests: XCTestCase {
    func testRoundTrip() throws {
        let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: tempDir) }

        let store = try ConfigStore(configDirectory: tempDir)
        var config = AppConfig.default
        config.plexURL = "http://127.0.0.1:32400"
        config.libraryPaths.moviesLibraryRoot = "/Volumes/Media/Movies"
        config.firstLaunchCompleted = true
        try store.save(config)
        let loaded = try store.load()
        XCTAssertEqual(loaded, config)
    }
}
