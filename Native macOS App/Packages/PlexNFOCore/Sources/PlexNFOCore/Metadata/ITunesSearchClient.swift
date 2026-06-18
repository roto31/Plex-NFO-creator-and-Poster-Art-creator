import Foundation

public final class ITunesSearchClient: @unchecked Sendable {
    private let session: URLSession
    private let minInterval: TimeInterval = 0.1
    private let lastRequestLock = NSLock()
    private var lastRequestTime: TimeInterval = 0

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func searchAlbum(title: String, artist: String) async throws -> [[String: Any]] {
        let json = try await get(
            url: URL(string: "https://itunes.apple.com/search")!,
            queryItems: [
                URLQueryItem(name: "term", value: "\(title) \(artist)"),
                URLQueryItem(name: "entity", value: "album"),
                URLQueryItem(name: "limit", value: "5"),
            ]
        )
        guard let results = json["results"] as? [[String: Any]] else { return [] }
        return results.filter { ($0["wrapperType"] as? String) == "collection" }
    }

    public func albumMetadata(collectionID: String) async throws -> AlbumMetadataRecord? {
        let json = try await get(
            url: URL(string: "https://itunes.apple.com/lookup")!,
            queryItems: [
                URLQueryItem(name: "id", value: collectionID),
                URLQueryItem(name: "entity", value: "song"),
            ]
        )
        guard let results = json["results"] as? [[String: Any]], let album = results.first else { return nil }
        guard (album["wrapperType"] as? String) == "collection" else { return nil }
        let releaseDate = album["releaseDate"] as? String ?? ""
        let year = Int(releaseDate.prefix(4)) ?? 0
        let rawArt = album["artworkUrl100"] as? String
        let genres = (album["primaryGenreName"] as? String).map { [$0] } ?? []
        return AlbumMetadataRecord(
            title: album["collectionName"] as? String ?? "",
            artist: album["artistName"] as? String ?? "Unknown Artist",
            year: year,
            genres: genres,
            appleID: collectionID,
            coverURL: rawArt.map { Self.upscaleArtwork($0) },
            trackCount: album["trackCount"] as? Int ?? 0
        )
    }

    public static func upscaleArtwork(_ url: String, size: Int = 3000) -> String {
        url.replacingOccurrences(of: #"\d+x\d+bb"#, with: "\(size)x\(size)bb", options: .regularExpression)
    }

    private func get(url: URL, queryItems: [URLQueryItem]) async throws -> [String: Any] {
        await waitForRateLimit()
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        components.queryItems = queryItems
        var request = URLRequest(url: components.url!)
        request.setValue("PlexNFOCreator/1.0", forHTTPHeaderField: "User-Agent")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else { return [:] }
        return (try? JSONSerialization.jsonObject(with: data) as? [String: Any]) ?? [:]
    }

    private func waitForRateLimit() async {
        lastRequestLock.lock()
        let elapsed = Date().timeIntervalSince1970 - lastRequestTime
        let wait = max(0, minInterval - elapsed)
        lastRequestLock.unlock()
        if wait > 0 {
            try? await Task.sleep(nanoseconds: UInt64(wait * 1_000_000_000))
        }
        lastRequestLock.lock()
        lastRequestTime = Date().timeIntervalSince1970
        lastRequestLock.unlock()
    }
}
