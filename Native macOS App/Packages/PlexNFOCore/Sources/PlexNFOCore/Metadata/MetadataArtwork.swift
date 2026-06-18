import Foundation

public enum MetadataArtwork {
    public static let movieArtFiles = [
        "poster.jpg", "folder.jpg", "backdrop.jpg",
        "clearart.png", "disc.png", "logo.png",
    ]

    public static let tvShowArtFiles = [
        "poster.jpg", "banner.jpg", "fanart.jpg",
        "clearart.png", "logo.png", "landscape.jpg",
    ]

    public static let musicAlbumArtFiles = ["folder.jpg", "cover.jpg"]

    public static func missingArtwork(in folder: URL, filenames: [String], force: Bool = false) -> Set<String> {
        if force { return Set(filenames) }
        let fm = FileManager.default
        return Set(filenames.filter { !fm.fileExists(atPath: folder.appendingPathComponent($0).path) })
    }

    public static func needsProcessing(
        folder: URL,
        nfoName: String,
        artFiles: [String],
        force: Bool = false
    ) -> (needsNFO: Bool, missingArt: Set<String>) {
        let nfoURL = folder.appendingPathComponent(nfoName)
        let needsNFO = force || !FileManager.default.fileExists(atPath: nfoURL.path)
        let missingArt = missingArtwork(in: folder, filenames: artFiles, force: force)
        return (needsNFO, missingArt)
    }
}
