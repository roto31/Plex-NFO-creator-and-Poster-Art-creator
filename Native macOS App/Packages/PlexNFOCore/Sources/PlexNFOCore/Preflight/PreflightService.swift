import Foundation

public struct PreflightResult: Sendable {
    public let canWriteConfig: Bool
    public let canWriteLibrary: Bool
    public let hasAPIKeys: Bool
    public let ffmpegAvailable: Bool
    public let messages: [String]

    public var ready: Bool { canWriteConfig && hasAPIKeys && canWriteLibrary }
}

public struct PreflightService: Sendable {
    private let keychain: KeychainStore

    public init(keychain: KeychainStore = KeychainStore()) {
        self.keychain = keychain
    }

    public func run(configStore: ConfigStore, config: AppConfig? = nil) -> PreflightResult {
        var messages: [String] = []
        let canWrite = probeWrite(configStore: configStore, messages: &messages)
        let loaded = config ?? (try? configStore.load())
        let canWriteLibrary = probeLibraryPaths(config: loaded, messages: &messages)
        let hasKeys = keychain.hasConfiguredAPIKeys()
        if !hasKeys { messages.append("Configure TMDB and TVDB API keys in Settings") }
        let ffmpegOK = FFmpegLocator.isAvailable()
        if !ffmpegOK { messages.append("ffmpeg not found; artwork extraction will be limited") }
        return PreflightResult(
            canWriteConfig: canWrite,
            canWriteLibrary: canWriteLibrary,
            hasAPIKeys: hasKeys,
            ffmpegAvailable: ffmpegOK,
            messages: messages
        )
    }

    private func probeLibraryPaths(config: AppConfig?, messages: inout [String]) -> Bool {
        guard let config else {
            messages.append("Library write probe skipped (no config)")
            return true
        }
        var paths: [String] = []
        paths.append(contentsOf: config.libraryPaths.moviesLibraryRoots)
        paths.append(contentsOf: config.libraryPaths.tvLibraryRoots)
        paths.append(contentsOf: config.libraryPaths.musicLibraryRoots)
        if !config.libraryPaths.moviesLibraryRoot.isEmpty { paths.append(config.libraryPaths.moviesLibraryRoot) }
        if !config.libraryPaths.tvLibraryRoot.isEmpty { paths.append(config.libraryPaths.tvLibraryRoot) }
        if !config.libraryPaths.musicLibraryRoot.isEmpty { paths.append(config.libraryPaths.musicLibraryRoot) }
        let unique = Array(Set(paths)).filter { !$0.isEmpty }
        guard !unique.isEmpty else {
            messages.append("Library write probe skipped (no library roots configured)")
            return true
        }
        var allOK = true
        for path in unique {
            if LibraryWriteProbe.checkWritePermission(at: path) {
                messages.append("Write permission OK: \(path)")
            } else {
                allOK = false
                messages.append("Cannot write to library path: \(path)")
            }
        }
        return allOK
    }

    private func probeWrite(configStore: ConfigStore, messages: inout [String]) -> Bool {
        do {
            let config = try configStore.load()
            try configStore.save(config)
            messages.append("Application Support write probe succeeded")
            return true
        } catch {
            messages.append("Cannot write config: \(error.localizedDescription)")
            return false
        }
    }
}
