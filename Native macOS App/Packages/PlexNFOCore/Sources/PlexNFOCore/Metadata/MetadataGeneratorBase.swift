import Foundation

public struct MetadataGeneratorOptions: Sendable {
    public var includeMusic: Bool
    public var libraryRoots: [String]
    public var force: Bool
    public var dryRun: Bool

    public init(includeMusic: Bool = false, libraryRoots: [String] = [], force: Bool = false, dryRun: Bool = false) {
        self.includeMusic = includeMusic
        self.libraryRoots = libraryRoots
        self.force = force
        self.dryRun = dryRun
    }
}

public struct MetadataScanResult: Sendable {
    public let path: String
    public let mediaType: MetadataMediaType
    public let needsNFO: Bool
    public let missingArtwork: [String]

    public init(path: String, mediaType: MetadataMediaType, needsNFO: Bool, missingArtwork: [String] = []) {
        self.path = path
        self.mediaType = mediaType
        self.needsNFO = needsNFO
        self.missingArtwork = missingArtwork
    }

    public var needsWork: Bool { needsNFO || !missingArtwork.isEmpty }
}

/// Library scanning and selective-processing helpers ported from plex_metadata_generator.py.
public enum MetadataGeneratorBase {
    private static let multipartPattern = #/(?i)(?:\bpart\s*\d+\b|\bpart\s+[ivxIVX]+\b|\bdisc\s*\d+\b|\bdisk\s*\d+\b|\b\d+\s+of\s+\d+\b|\bvol(?:ume)?\s*\d+\b|\bchapter\s*\d+\b|\bpt\s*\d+\b)/#

    private static let videoExtensions: Set<String> = ["mkv", "mp4", "avi", "m4v", "mov"]
    private static let audioExtensions: Set<String> = ["mp3", "flac", "m4a", "aac", "ogg", "wav"]

    public static func isMultipart(_ name: String) -> Bool {
        name.firstMatch(of: multipartPattern) != nil
    }

    public static func scanMissingNFO(
        roots: [String],
        extensions: Set<String> = ["mkv", "mp4", "avi"],
        force: Bool = false
    ) -> [MetadataScanResult] {
        var results: [MetadataScanResult] = []
        let fm = FileManager.default
        for root in roots where !root.isEmpty {
            let rootURL = URL(fileURLWithPath: root)
            guard let enumerator = fm.enumerator(at: rootURL, includingPropertiesForKeys: [.isDirectoryKey]) else { continue }
            for case let fileURL as URL in enumerator {
                guard extensions.contains(fileURL.pathExtension.lowercased()) else { continue }
                let nfo = fileURL.deletingPathExtension().appendingPathExtension("nfo")
                let needs = force || !fm.fileExists(atPath: nfo.path)
                results.append(MetadataScanResult(path: fileURL.path, mediaType: .video, needsNFO: needs))
            }
        }
        return results
    }

    public static func scanLibrary(
        tvRoots: [String],
        movieRoots: [String],
        musicRoots: [String],
        includeMusic: Bool,
        force: Bool = false
    ) -> [MetadataScanResult] {
        var results: [MetadataScanResult] = []
        for root in tvRoots where !root.isEmpty {
            results.append(contentsOf: scanTVLibrary(root: root, force: force))
        }
        for root in movieRoots where !root.isEmpty {
            results.append(contentsOf: scanMovieLibrary(root: root, force: force))
        }
        if includeMusic {
            for root in musicRoots where !root.isEmpty {
                results.append(contentsOf: scanMusicLibrary(root: root, force: force))
            }
        }
        return results
    }

    public static func scanTVLibrary(root: String, force: Bool = false) -> [MetadataScanResult] {
        let rootURL = URL(fileURLWithPath: root)
        let fm = FileManager.default
        guard let showDirs = try? fm.contentsOfDirectory(at: rootURL, includingPropertiesForKeys: [.isDirectoryKey]) else {
            return []
        }
        var results: [MetadataScanResult] = []
        for showDir in showDirs where showDir.hasDirectoryPath && !showDir.lastPathComponent.hasPrefix(".") {
            if isMultipart(showDir.lastPathComponent) { continue }
            let showCheck = MetadataArtwork.needsProcessing(
                folder: showDir,
                nfoName: "tvshow.nfo",
                artFiles: MetadataArtwork.tvShowArtFiles,
                force: force
            )
            if showCheck.needsNFO || !showCheck.missingArt.isEmpty {
                results.append(MetadataScanResult(
                    path: showDir.path,
                    mediaType: .tvShow,
                    needsNFO: showCheck.needsNFO,
                    missingArtwork: Array(showCheck.missingArt)
                ))
            }
            if let seasons = try? fm.contentsOfDirectory(at: showDir, includingPropertiesForKeys: [.isDirectoryKey]) {
                for seasonDir in seasons where seasonDir.hasDirectoryPath {
                    let seasonName = seasonDir.lastPathComponent.lowercased()
                    guard seasonName.hasPrefix("season") else { continue }
                    if let episodes = try? fm.contentsOfDirectory(at: seasonDir, includingPropertiesForKeys: nil) {
                        for episode in episodes where videoExtensions.contains(episode.pathExtension.lowercased()) {
                            let nfo = episode.deletingPathExtension().appendingPathExtension("nfo")
                            let needs = force || !fm.fileExists(atPath: nfo.path)
                            if needs {
                                results.append(MetadataScanResult(path: episode.path, mediaType: .tvShow, needsNFO: needs))
                            }
                        }
                    }
                }
            }
        }
        return results
    }

    public static func scanMovieLibrary(root: String, force: Bool = false) -> [MetadataScanResult] {
        let rootURL = URL(fileURLWithPath: root)
        let fm = FileManager.default
        guard let entries = try? fm.contentsOfDirectory(at: rootURL, includingPropertiesForKeys: [.isDirectoryKey]) else {
            return []
        }
        var results: [MetadataScanResult] = []
        for entry in entries {
            if entry.hasDirectoryPath {
                if isMultipart(entry.lastPathComponent) { continue }
                let check = MetadataArtwork.needsProcessing(
                    folder: entry,
                    nfoName: "\(entry.lastPathComponent).nfo",
                    artFiles: MetadataArtwork.movieArtFiles,
                    force: force
                )
                if check.needsNFO || !check.missingArt.isEmpty {
                    results.append(MetadataScanResult(
                        path: entry.path,
                        mediaType: .movie,
                        needsNFO: check.needsNFO,
                        missingArtwork: Array(check.missingArt)
                    ))
                }
            } else if videoExtensions.contains(entry.pathExtension.lowercased()) {
                let folder = entry.deletingLastPathComponent()
                let nfoName = "\(entry.deletingPathExtension().lastPathComponent).nfo"
                let check = MetadataArtwork.needsProcessing(folder: folder, nfoName: nfoName, artFiles: MetadataArtwork.movieArtFiles, force: force)
                if check.needsNFO || !check.missingArt.isEmpty {
                    results.append(MetadataScanResult(
                        path: entry.path,
                        mediaType: .movie,
                        needsNFO: check.needsNFO,
                        missingArtwork: Array(check.missingArt)
                    ))
                }
            }
        }
        return results
    }

    public static func scanMusicLibrary(root: String, force: Bool = false) -> [MetadataScanResult] {
        let rootURL = URL(fileURLWithPath: root)
        let fm = FileManager.default
        guard let artistDirs = try? fm.contentsOfDirectory(at: rootURL, includingPropertiesForKeys: [.isDirectoryKey]) else {
            return []
        }
        var results: [MetadataScanResult] = []
        for artistDir in artistDirs where artistDir.hasDirectoryPath && !artistDir.lastPathComponent.hasPrefix(".") {
            guard let albumDirs = try? fm.contentsOfDirectory(at: artistDir, includingPropertiesForKeys: [.isDirectoryKey]) else {
                continue
            }
            for albumDir in albumDirs where albumDir.hasDirectoryPath {
                let hasTracks = (try? fm.contentsOfDirectory(at: albumDir, includingPropertiesForKeys: nil))?
                    .contains { audioExtensions.contains($0.pathExtension.lowercased()) } ?? false
                guard hasTracks else { continue }
                let check = MetadataArtwork.needsProcessing(
                    folder: albumDir,
                    nfoName: "album.nfo",
                    artFiles: MetadataArtwork.musicAlbumArtFiles,
                    force: force
                )
                if check.needsNFO || !check.missingArt.isEmpty {
                    results.append(MetadataScanResult(
                        path: albumDir.path,
                        mediaType: .musicAlbum,
                        needsNFO: check.needsNFO,
                        missingArtwork: Array(check.missingArt)
                    ))
                }
            }
        }
        return results
    }
}
