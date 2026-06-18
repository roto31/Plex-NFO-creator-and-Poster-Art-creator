import Foundation

public enum MetadataMediaType: String, Sendable, Codable {
    case tvShow
    case movie
    case musicAlbum
    case musicArtist
    case musicTrack
    case video
}

public struct ShowMetadataRecord: Sendable {
    public var title: String
    public var year: Int
    public var plot: String
    public var rating: Double
    public var tvdbID: Int?
    public var tmdbID: Int?
    public var imdbID: String?
    public var genres: [String]
    public var runtime: Int
    public var status: String

    public init(
        title: String,
        year: Int = 0,
        plot: String = "",
        rating: Double = 0,
        tvdbID: Int? = nil,
        tmdbID: Int? = nil,
        imdbID: String? = nil,
        genres: [String] = [],
        runtime: Int = 45,
        status: String = "Continuing"
    ) {
        self.title = title
        self.year = year
        self.plot = plot
        self.rating = rating
        self.tvdbID = tvdbID
        self.tmdbID = tmdbID
        self.imdbID = imdbID
        self.genres = genres
        self.runtime = runtime
        self.status = status
    }
}

public struct AlbumMetadataRecord: Sendable {
    public var title: String
    public var artist: String
    public var year: Int
    public var plot: String
    public var genres: [String]
    public var mbid: String?
    public var appleID: String?
    public var coverURL: String?
    public var trackCount: Int

    public init(
        title: String,
        artist: String,
        year: Int = 0,
        plot: String = "",
        genres: [String] = [],
        mbid: String? = nil,
        appleID: String? = nil,
        coverURL: String? = nil,
        trackCount: Int = 0
    ) {
        self.title = title
        self.artist = artist
        self.year = year
        self.plot = plot
        self.genres = genres
        self.mbid = mbid
        self.appleID = appleID
        self.coverURL = coverURL
        self.trackCount = trackCount
    }
}

public struct MetadataRunSummary: Sendable {
    public let scanned: Int
    public let nfoWritten: Int
    public let skipped: Int
    public let errors: Int
    public let messages: [String]

    public var description: String {
        var lines = [
            "Scanned: \(scanned)",
            "NFO written: \(nfoWritten)",
            "Skipped: \(skipped)",
            "Errors: \(errors)",
        ]
        lines.append(contentsOf: messages.prefix(20))
        return lines.joined(separator: "\n")
    }
}
