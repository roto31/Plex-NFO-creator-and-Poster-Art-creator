import Foundation

public enum LibraryWriteProbe {
    public static let probeFileName = ".plex_nfo_write_test"

    /// Matches `preflight.py` `check_write_permission`: touch and remove probe file in target dir.
    public static func checkWritePermission(at path: String, fileManager: FileManager = .default) -> Bool {
        let directory = URL(fileURLWithPath: path, isDirectory: true)
        guard fileManager.fileExists(atPath: directory.path) else { return false }
        let probe = directory.appendingPathComponent(probeFileName)
        do {
            try Data().write(to: probe)
            try fileManager.removeItem(at: probe)
            return true
        } catch {
            return false
        }
    }
}
