import Foundation

public struct RenameResult: Sendable {
    public let from: URL
    public let to: URL?
    public let skipped: Bool
    public let reason: String?

    public init(from: URL, to: URL? = nil, skipped: Bool = false, reason: String? = nil) {
        self.from = from
        self.to = to
        self.skipped = skipped
        self.reason = reason
    }
}

public enum RenameModuleError: Error, LocalizedError {
    case invalidPath(URL)
    case moveFailed(URL, URL)

    public var errorDescription: String? {
        switch self {
        case .invalidPath(let url): return "Invalid path: \(url.path)"
        case .moveFailed(let from, let to): return "Could not move \(from.lastPathComponent) to \(to.path)"
        }
    }
}

/// Ports rename_movies.py folder normalization for Plex-friendly movie folders.
public enum RenameModule {
    private static let videoExtensions: Set<String> = ["mkv", "mp4", "avi", "m4v", "mov", "wmv", "flv", "webm"]

    public static func sanitizeFolderName(_ name: String) -> String {
        var result = name
        result = result.replacingOccurrences(of: "_", with: " ")
        result = result.replacingOccurrences(of: ".", with: " ")
        while result.contains("  ") { result = result.replacingOccurrences(of: "  ", with: " ") }
        return result.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    public static func isVideoFile(_ url: URL) -> Bool {
        videoExtensions.contains(url.pathExtension.lowercased())
    }

    public static func proposedFolderName(for movieFolder: URL) -> String {
        sanitizeFolderName(movieFolder.lastPathComponent)
    }

    public static func renameMovieFolder(
        at folderURL: URL,
        dryRun: Bool = false,
        fileManager: FileManager = .default
    ) throws -> RenameResult {
        guard fileManager.fileExists(atPath: folderURL.path) else {
            throw RenameModuleError.invalidPath(folderURL)
        }
        let proposed = proposedFolderName(for: folderURL)
        let parent = folderURL.deletingLastPathComponent()
        let target = parent.appendingPathComponent(proposed, isDirectory: true)
        if folderURL.standardizedFileURL == target.standardizedFileURL {
            return RenameResult(from: folderURL, skipped: true, reason: "Already normalized")
        }
        if fileManager.fileExists(atPath: target.path) {
            return RenameResult(from: folderURL, skipped: true, reason: "Target exists")
        }
        if dryRun {
            return RenameResult(from: folderURL, to: target)
        }
        do {
            try fileManager.moveItem(at: folderURL, to: target)
            return RenameResult(from: folderURL, to: target)
        } catch {
            throw RenameModuleError.moveFailed(folderURL, target)
        }
    }

    public static func renameMovies(
        in root: URL,
        dryRun: Bool = false,
        onProgress: ((Int, Int, String) -> Void)? = nil
    ) throws -> [RenameResult] {
        let fm = FileManager.default
        guard let entries = try? fm.contentsOfDirectory(at: root, includingPropertiesForKeys: [.isDirectoryKey], options: [.skipsHiddenFiles]) else {
            throw RenameModuleError.invalidPath(root)
        }
        let folders = entries.filter { url in
            (try? url.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true
        }
        var results: [RenameResult] = []
        let total = folders.count
        for (index, folder) in folders.enumerated() {
            onProgress?(index + 1, total, folder.lastPathComponent)
            let result = try renameMovieFolder(at: folder, dryRun: dryRun)
            results.append(result)
        }
        return results
    }
}
