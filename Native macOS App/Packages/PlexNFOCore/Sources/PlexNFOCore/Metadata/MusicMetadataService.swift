import Foundation

public struct MusicMetadataRequest: Sendable {
    public let libraryRoot: URL
    public let settings: MetadataGeneratorSettings

    public init(libraryRoot: URL, settings: MetadataGeneratorSettings = .default) {
        self.libraryRoot = libraryRoot
        self.settings = settings
    }
}

public struct MusicMetadataService: Sendable {
    private let keychain: KeychainStore
    private let session: URLSession

    public init(keychain: KeychainStore = KeychainStore(), session: URLSession = .shared) {
        self.keychain = keychain
        self.session = session
    }

    public func run(request: MusicMetadataRequest) async throws -> String {
        let artistDirs = try FileManager.default.contentsOfDirectory(
            at: request.libraryRoot,
            includingPropertiesForKeys: [.isDirectoryKey]
        ).filter(\.hasDirectoryPath)

        var written = 0
        for artistDir in artistDirs {
            let albumDirs = try FileManager.default.contentsOfDirectory(
                at: artistDir,
                includingPropertiesForKeys: [.isDirectoryKey]
            ).filter(\.hasDirectoryPath)
            for albumDir in albumDirs {
                let scan = MetadataGeneratorBase.scanMusicLibrary(root: albumDir.deletingLastPathComponent().path)
                guard scan.contains(where: { $0.path == albumDir.path && $0.needsNFO }) else { continue }
                let metadata = try await lookupAlbum(
                    title: albumDir.lastPathComponent,
                    artist: artistDir.lastPathComponent,
                    settings: request.settings
                )
                guard let metadata else { continue }
                let nfo = MetadataNFOGenerator.albumNFO(metadata)
                try nfo.write(to: albumDir.appendingPathComponent("album.nfo"), atomically: true, encoding: .utf8)
                written += 1
            }
        }
        return "Music metadata: wrote \(written) album NFO files"
    }

    public func lookupAlbum(title: String, artist: String, settings: MetadataGeneratorSettings) async throws -> AlbumMetadataRecord? {
        if settings.appleMusicKit.enabled,
           !settings.appleMusicKit.teamID.isEmpty,
           !settings.appleMusicKit.keyID.isEmpty {
            if let pem = try loadMusicKitPrivateKey(settings: settings) {
                let creds = AppleMusicKitTokenGenerator.Credentials(
                    teamID: settings.appleMusicKit.teamID,
                    keyID: settings.appleMusicKit.keyID,
                    privateKeyPEM: pem
                )
                let client = AppleMusicKitClient(
                    credentials: creds,
                    storefront: settings.appleMusicKit.storefront,
                    session: session
                )
                let results = try await client.searchAlbum(term: "\(title) \(artist)")
                if let first = results.first, let metadata = client.albumMetadata(from: first) {
                    return metadata
                }
            }
        }

        let itunes = ITunesSearchClient(session: session)
        let itunesResults = try await itunes.searchAlbum(title: title, artist: artist)
        if let first = itunesResults.first,
           let collectionID = first["collectionId"].map({ String(describing: $0) }),
           let metadata = try await itunes.albumMetadata(collectionID: collectionID) {
            return metadata
        }

        let mb = MusicBrainzClient(contactEmail: settings.musicBrainzContact, session: session)
        let releases = try await mb.searchRelease(album: title, artist: artist)
        if let first = releases.first, let id = first["id"] as? String {
            return try await mb.releaseMetadata(mbid: id)
        }
        return nil
    }

    private func loadMusicKitPrivateKey(settings: MetadataGeneratorSettings) throws -> String? {
        if let keychainPEM = try keychain.get(.appleMusicKitPrivateKey), !keychainPEM.isEmpty {
            return keychainPEM
        }
        let path = settings.appleMusicKit.privateKeyPath
        guard !path.isEmpty else { return nil }
        return try String(contentsOf: URL(fileURLWithPath: path), encoding: .utf8)
    }
}
