import Foundation

public struct HealthCheckOptions: Sendable {
    public var skipNetwork: Bool

    public init(skipNetwork: Bool = false) {
        self.skipNetwork = skipNetwork
    }
}

public struct DiskSpaceInfo: Sendable, Equatable {
    public let path: String
    public let totalBytes: Int64
    public let freeBytes: Int64
    public let usedPercent: Double

    public init(path: String, totalBytes: Int64, freeBytes: Int64) {
        self.path = path
        self.totalBytes = totalBytes
        self.freeBytes = freeBytes
        let used = Double(totalBytes - freeBytes)
        self.usedPercent = totalBytes > 0 ? (used / Double(totalBytes)) * 100 : 0
    }
}

public enum DiskSpaceChecker {
    public static func usage(at path: String) -> DiskSpaceInfo? {
        guard FileManager.default.fileExists(atPath: path) else { return nil }
        guard let attrs = try? FileManager.default.attributesOfFileSystem(forPath: path),
              let total = attrs[.systemSize] as? Int64,
              let free = attrs[.systemFreeSize] as? Int64 else { return nil }
        return DiskSpaceInfo(path: path, totalBytes: total, freeBytes: free)
    }
}

public struct HealthCheckResult: Sendable {
    public struct Check: Sendable {
        public let name: String
        public let passed: Bool
        public let detail: String
    }

    public let checks: [Check]
    public var allPassed: Bool { checks.allSatisfy(\.passed) }
}

public struct HealthCheckService: Sendable {
    private let config: AppConfig
    private let keychain: KeychainStore
    private let options: HealthCheckOptions
    private let session: URLSession

    public init(
        config: AppConfig,
        keychain: KeychainStore = KeychainStore(),
        options: HealthCheckOptions = .init(),
        session: URLSession = .shared
    ) {
        self.config = config
        self.keychain = keychain
        self.options = options
        self.session = session
    }

    public func run() async -> HealthCheckResult {
        var checks: [HealthCheckResult.Check] = []
        checks.append(checkConfiguration())
        checks.append(checkAPIKeys())
        checks.append(checkLibraryPaths())
        checks.append(checkTunarrDatabase())
        checks.append(checkScheduling())
        checks.append(checkLogs())
        checks.append(checkDiskSpace())
        checks.append(checkCacheDirectory())
        if !options.skipNetwork {
            checks.append(await checkPlexConnectivity())
            checks.append(await checkTVDBConnectivity())
            checks.append(await checkTMDBConnectivity())
            checks.append(await checkFanartConnectivity())
        }
        return HealthCheckResult(checks: checks)
    }

    private func checkConfiguration() -> HealthCheckResult.Check {
        let roots = MetadataGeneratorConfig.resolveRoots(from: config.libraryPaths)
        let hasLibrary = !roots.tv.isEmpty || !roots.movies.isEmpty || !roots.music.isEmpty
        return .init(
            name: "Configuration",
            passed: hasLibrary,
            detail: hasLibrary ? "Library paths configured" : "No library roots configured"
        )
    }

    private func checkAPIKeys() -> HealthCheckResult.Check {
        let tmdb = (try? keychain.get(.tmdbAPIKey))?.isEmpty == false
        let tvdb = (try? keychain.get(.tvdbAPIKey))?.isEmpty == false
        let passed = tmdb && tvdb
        return .init(
            name: "API Keys",
            passed: passed,
            detail: passed ? "TMDB and TVDB keys present in Keychain" : "Missing TMDB or TVDB API key"
        )
    }

    private func checkLibraryPaths() -> HealthCheckResult.Check {
        let roots = MetadataGeneratorConfig.resolveRoots(from: config.libraryPaths)
        let paths = roots.tv + roots.movies + roots.music
        let existing = paths.filter { FileManager.default.fileExists(atPath: $0) }
        let passed = !paths.isEmpty && existing.count == paths.count
        return .init(
            name: "Library Paths",
            passed: passed,
            detail: "\(existing.count)/\(paths.count) paths exist on disk"
        )
    }

    private func checkTunarrDatabase() -> HealthCheckResult.Check {
        let path = config.metadataSettings.tunarrDBPath
        guard !path.isEmpty else {
            return .init(name: "Tunarr DB", passed: true, detail: "Tunarr not configured (optional)")
        }
        let exists = FileManager.default.fileExists(atPath: path)
        return .init(
            name: "Tunarr DB",
            passed: exists,
            detail: exists ? "Tunarr database found" : "Tunarr database missing at \(path)"
        )
    }

    private func checkScheduling() -> HealthCheckResult.Check {
        let schedule = config.metadataSettings.scheduling
        let plist = LaunchAgentScheduler.plistURL()
        let exists = FileManager.default.fileExists(atPath: plist.path)
        if schedule.enabled {
            return .init(
                name: "Daily Scheduling",
                passed: exists,
                detail: exists
                    ? "Launch agent installed for \(String(format: "%02d:%02d", schedule.hour, schedule.minute))"
                    : "Scheduling enabled but launch agent not installed"
            )
        }
        return .init(
            name: "Daily Scheduling",
            passed: true,
            detail: exists ? "Launch agent present (scheduling disabled in app)" : "Scheduling disabled"
        )
    }

    private func checkLogs() -> HealthCheckResult.Check {
        let logDir = URL(fileURLWithPath: MetadataGeneratorConfig.defaultLogDirectory())
        let exists = FileManager.default.fileExists(atPath: logDir.path)
        return .init(
            name: "Logs",
            passed: exists,
            detail: exists ? "Log directory present" : "Log directory will be created on first run"
        )
    }

    private func checkDiskSpace() -> HealthCheckResult.Check {
        let roots = MetadataGeneratorConfig.resolveRoots(from: config.libraryPaths)
        let probePath = roots.tv.first ?? roots.movies.first ?? roots.music.first ?? NSHomeDirectory()
        guard let info = DiskSpaceChecker.usage(at: probePath) else {
            return .init(name: "Disk Space", passed: false, detail: "Could not read disk usage for \(probePath)")
        }
        let passed = info.usedPercent < 95
        let freeGB = Double(info.freeBytes) / 1_073_741_824
        return .init(
            name: "Disk Space",
            passed: passed,
            detail: String(format: "%.1f%% used on %@ (%.1f GB free)", info.usedPercent, probePath, freeGB)
        )
    }

    private func checkCacheDirectory() -> HealthCheckResult.Check {
        let cache = config.metadataSettings.cacheDirectory.isEmpty
            ? MetadataGeneratorConfig.defaultCacheDirectory()
            : config.metadataSettings.cacheDirectory
        let exists = FileManager.default.fileExists(atPath: cache)
        return .init(
            name: "Cache Directory",
            passed: true,
            detail: exists ? "Cache directory present" : "Cache directory will be created on demand"
        )
    }

    private func checkPlexConnectivity() async -> HealthCheckResult.Check {
        let token = (try? keychain.get(.plexToken)) ?? ""
        let client = PlexClient(baseURL: config.plexURL, token: token, session: session)
        let result = await client.connectivityCheck()
        return .init(name: "Plex API", passed: result.ok, detail: result.detail)
    }

    private func checkTVDBConnectivity() async -> HealthCheckResult.Check {
        guard let apiKey = try? keychain.get(.tvdbAPIKey), !apiKey.isEmpty else {
            return .init(name: "TVDb API", passed: false, detail: "TVDb API key not configured")
        }
        var client = TVDBClient(apiKey: apiKey, session: session)
        do {
            try await client.login()
            return .init(name: "TVDb API", passed: true, detail: "TVDb API reachable")
        } catch {
            return .init(name: "TVDb API", passed: false, detail: error.localizedDescription)
        }
    }

    private func checkTMDBConnectivity() async -> HealthCheckResult.Check {
        guard let apiKey = try? keychain.get(.tmdbAPIKey), !apiKey.isEmpty else {
            return .init(name: "TMDb API", passed: false, detail: "TMDb API key not configured")
        }
        let client = TMDBClient(apiKey: apiKey, session: session)
        do {
            _ = try await client.searchMovie(query: "test")
            return .init(name: "TMDb API", passed: true, detail: "TMDb API reachable")
        } catch {
            return .init(name: "TMDb API", passed: false, detail: error.localizedDescription)
        }
    }

    private func checkFanartConnectivity() async -> HealthCheckResult.Check {
        guard let apiKey = try? keychain.get(.fanartAPIKey), !apiKey.isEmpty else {
            return .init(name: "FanArt.tv", passed: true, detail: "FanArt.tv key not configured (optional)")
        }
        var components = URLComponents(string: "https://webservice.fanart.tv/v3/movies/550")!
        components.queryItems = [URLQueryItem(name: "api_key", value: apiKey)]
        guard let url = components.url else {
            return .init(name: "FanArt.tv", passed: false, detail: "Invalid FanArt.tv URL")
        }
        do {
            let (_, response) = try await session.data(from: url)
            let code = (response as? HTTPURLResponse)?.statusCode ?? 0
            return .init(
                name: "FanArt.tv",
                passed: code == 200,
                detail: code == 200 ? "FanArt.tv API reachable" : "FanArt.tv returned HTTP \(code)"
            )
        } catch {
            return .init(name: "FanArt.tv", passed: false, detail: error.localizedDescription)
        }
    }
}
