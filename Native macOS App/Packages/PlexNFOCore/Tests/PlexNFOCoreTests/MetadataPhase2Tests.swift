import XCTest
@testable import PlexNFOCore

final class MetadataGeneratorConfigTests: XCTestCase {
    func testParseDailyTime() {
        let early = MetadataSchedulingConfig.parseDailyTime("02:00")
        XCTAssertEqual(early?.hour, 2)
        XCTAssertEqual(early?.minute, 0)
        let late = MetadataSchedulingConfig.parseDailyTime("23:59")
        XCTAssertEqual(late?.hour, 23)
        XCTAssertEqual(late?.minute, 59)
        XCTAssertNil(MetadataSchedulingConfig.parseDailyTime("25:00"))
    }

    func testImportLegacyJSON() throws {
        let json = """
        {
          "tv_library_root": "/media/TV",
          "movies_library_root": "/media/Movies",
          "music_library_root": "/media/Music",
          "tunarr": { "db_path": "/opt/tunarr/cache/tunarr.db" },
          "plex": { "tv_library_key": "1", "movies_library_key": "2", "music_library_key": "3" },
          "scheduling": { "enabled": true, "daily_time": "03:30" }
        }
        """.data(using: .utf8)!
        let imported = try MetadataGeneratorConfig.importLegacyJSON(json)
        XCTAssertEqual(imported.libraryPaths.tvLibraryRoot, "/media/TV")
        XCTAssertEqual(imported.settings.tunarrDBPath, "/opt/tunarr/cache/tunarr.db")
        XCTAssertEqual(imported.settings.scheduling.hour, 3)
        XCTAssertEqual(imported.settings.scheduling.minute, 30)
        XCTAssertTrue(imported.settings.scheduling.enabled)
    }
}

final class MetadataGeneratorBaseTests: XCTestCase {
    func testIsMultipart() {
        XCTAssertTrue(MetadataGeneratorBase.isMultipart("Movie Part 2"))
        XCTAssertTrue(MetadataGeneratorBase.isMultipart("Disc 1"))
        XCTAssertFalse(MetadataGeneratorBase.isMultipart("Breaking Bad"))
    }

    func testScanTVLibraryDetectsMissingNFO() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let show = root.appendingPathComponent("Test Show", isDirectory: true)
        try FileManager.default.createDirectory(at: show, withIntermediateDirectories: true)
        let results = MetadataGeneratorBase.scanTVLibrary(root: root.path)
        XCTAssertEqual(results.count, 1)
        XCTAssertTrue(results[0].needsNFO)
        XCTAssertEqual(results[0].mediaType, .tvShow)
    }
}

final class SchedulingServiceTests: XCTestCase {
    func testPlistContainsCalendarInterval() {
        let config = LaunchdScheduleConfig(enabled: true, hour: 2, minute: 15)
        let plist = SchedulingService.plistContent(
            config: config,
            executablePath: "/Applications/PlexNFOCreator.app/Contents/MacOS/PlexNFOCreator",
            logDirectory: "/tmp/logs"
        )
        XCTAssertTrue(plist.contains("StartCalendarInterval"))
        XCTAssertTrue(plist.contains("<integer>2</integer>"))
        XCTAssertTrue(plist.contains("<integer>15</integer>"))
        XCTAssertTrue(plist.contains("--metadata-scheduled"))
    }

    func testAgentPath() {
        let url = SchedulingService.agentPath(for: LaunchAgentScheduler.label)
        XCTAssertTrue(url.path.hasSuffix("com.roto31.PlexNFOCreator.metadata.plist"))
    }
}

final class HealthCheckServiceTests: XCTestCase {
    func testDiskSpaceChecker() throws {
        let temp = FileManager.default.temporaryDirectory
        let info = DiskSpaceChecker.usage(at: temp.path)
        XCTAssertNotNil(info)
        XCTAssertGreaterThan(info?.totalBytes ?? 0, 0)
    }

    func testHealthCheckSkipsNetwork() async {
        var config = AppConfig.default
        config.libraryPaths.tvLibraryRoot = NSHomeDirectory()
        let service = HealthCheckService(config: config, options: HealthCheckOptions(skipNetwork: true))
        let result = await service.run()
        XCTAssertFalse(result.checks.isEmpty)
        XCTAssertNil(result.checks.first { $0.name == "Plex API" })
    }
}
