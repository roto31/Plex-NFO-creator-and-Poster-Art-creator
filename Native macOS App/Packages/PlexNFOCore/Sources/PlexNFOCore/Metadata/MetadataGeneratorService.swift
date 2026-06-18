import Foundation

public struct MetadataGeneratorRequest: Sendable {
    public let options: MetadataGeneratorOptions
    public let config: AppConfig
    public let settings: MetadataGeneratorSettings

    public init(options: MetadataGeneratorOptions, config: AppConfig, settings: MetadataGeneratorSettings) {
        self.options = options
        self.config = config
        self.settings = settings
    }
}

public struct MetadataProgressReporter: Sendable {
    public var onLog: @Sendable (String) -> Void
    public var onProgress: @Sendable (Int, Int, String) -> Void

    public init(
        onLog: @escaping @Sendable (String) -> Void = { _ in },
        onProgress: @escaping @Sendable (Int, Int, String) -> Void = { _, _, _ in }
    ) {
        self.onLog = onLog
        self.onProgress = onProgress
    }
}

public struct MetadataGeneratorService: Sendable {
    private let keychain: KeychainStore
    private let logging: LoggingService
    private let session: URLSession

    public init(keychain: KeychainStore = KeychainStore(), logging: LoggingService = LoggingService(), session: URLSession = .shared) {
        self.keychain = keychain
        self.logging = logging
        self.session = session
    }

    public func run(request: MetadataGeneratorRequest, reporter: MetadataProgressReporter = .init()) async throws -> MetadataRunSummary {
        let roots = MetadataGeneratorConfig.resolveRoots(from: request.config.libraryPaths)
        let scan = MetadataGeneratorBase.scanLibrary(
            tvRoots: roots.tv,
            movieRoots: roots.movies,
            musicRoots: roots.music,
            includeMusic: request.options.includeMusic,
            force: request.options.force
        )
        let workItems = scan.filter(\.needsWork)
        reporter.onLog("Found \(workItems.count) items needing metadata work (of \(scan.count) scanned)")
        logging.info("Metadata scan: \(workItems.count) items need work", category: .metadata)

        if request.options.dryRun {
            return MetadataRunSummary(
                scanned: scan.count,
                nfoWritten: 0,
                skipped: workItems.count,
                errors: 0,
                messages: ["Dry run — no files written"]
            )
        }

        let musicService = MusicMetadataService(keychain: keychain, session: session)
        var nfoWritten = 0
        var errors = 0
        var messages: [String] = []
        let total = max(workItems.count, 1)

        for (index, item) in workItems.enumerated() {
            reporter.onProgress(index + 1, total, item.path)
            do {
                switch item.mediaType {
                case .musicAlbum:
                    guard request.options.includeMusic else { continue }
                    let albumURL = URL(fileURLWithPath: item.path)
                    let artist = albumURL.deletingLastPathComponent().lastPathComponent
                    let album = albumURL.lastPathComponent
                    let metadata = try await musicService.lookupAlbum(
                        title: album,
                        artist: artist,
                        settings: request.settings
                    )
                    if item.needsNFO, let metadata {
                        let nfo = MetadataNFOGenerator.albumNFO(metadata)
                        let nfoURL = albumURL.appendingPathComponent("album.nfo")
                        try nfo.write(to: nfoURL, atomically: true, encoding: .utf8)
                        nfoWritten += 1
                        messages.append("Wrote album NFO: \(album)")
                    }
                case .tvShow:
                    let showURL = URL(fileURLWithPath: item.path)
                    let showName = showURL.lastPathComponent
                    if item.needsNFO {
                        var plot = ""
                        if !request.settings.tunarrDBPath.isEmpty {
                            let tunarr = TunarrMetadataProvider(dbPath: request.settings.tunarrDBPath)
                            if let lookup = tunarr.lookupShow(title: showName) {
                                plot = lookup.summary
                            }
                        }
                        let showMeta = ShowMetadataRecord(title: showName, plot: plot)
                        let nfo = MetadataNFOGenerator.showNFO(showMeta)
                        try nfo.write(to: showURL.appendingPathComponent("tvshow.nfo"), atomically: true, encoding: .utf8)
                        nfoWritten += 1
                        messages.append("Wrote tvshow NFO: \(showName)")
                    }
                    if !item.missingArtwork.isEmpty {
                        messages.append("Missing artwork for \(showName): \(item.missingArtwork.joined(separator: ", "))")
                    }
                case .movie:
                    if item.needsNFO {
                        let pathURL = URL(fileURLWithPath: item.path)
                        let title = pathURL.hasDirectoryPath ? pathURL.lastPathComponent : pathURL.deletingPathExtension().lastPathComponent
                        let folder = pathURL.hasDirectoryPath ? pathURL : pathURL.deletingLastPathComponent()
                        let nfoName = "\(title).nfo"
                        let nfo = NFOSerializer.movieNFO(title: title, year: nil, tmdbID: nil, plot: nil)
                        try nfo.write(to: folder.appendingPathComponent(nfoName), atomically: true, encoding: .utf8)
                        nfoWritten += 1
                        messages.append("Wrote movie NFO: \(title)")
                    }
                default:
                    continue
                }
            } catch {
                errors += 1
                let message = "Error processing \(item.path): \(error.localizedDescription)"
                messages.append(message)
                logging.error(message, category: .metadata)
            }
        }

        if request.settings.subtitlesEnabled {
            reporter.onLog("Subtitle download/embed not yet ported — enable in a future release")
        }

        if let token = try? keychain.get(.plexToken), !token.isEmpty {
            let plex = PlexClient(baseURL: request.config.plexURL, token: token, session: session)
            for key in [request.settings.plexTVLibraryKey, request.settings.plexMoviesLibraryKey, request.settings.plexMusicLibraryKey]
                where !key.isEmpty {
                do {
                    try await plex.refreshLibrary(sectionKey: key)
                    reporter.onLog("Refreshed Plex library section \(key)")
                } catch {
                    reporter.onLog("Plex refresh failed for section \(key): \(error.localizedDescription)")
                }
            }
        }

        return MetadataRunSummary(
            scanned: scan.count,
            nfoWritten: nfoWritten,
            skipped: scan.count - workItems.count,
            errors: errors,
            messages: messages
        )
    }
}
