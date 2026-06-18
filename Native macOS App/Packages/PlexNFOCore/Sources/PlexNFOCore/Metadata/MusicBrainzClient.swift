import Foundation

public final class MusicBrainzClient: @unchecked Sendable {
    private let userAgent: String
    private let session: URLSession
    private let minInterval: TimeInterval = 1.1
    private let lastRequestLock = NSLock()
    private var lastRequestTime: TimeInterval = 0

    public init(contactEmail: String, session: URLSession = .shared) {
        let email = contactEmail.isEmpty ? "contact@example.com" : contactEmail
        self.userAgent = "PlexNFOCreator/1.0 (+\(email))"
        self.session = session
    }

    public func searchRelease(album: String, artist: String) async throws -> [[String: Any]] {
        try await rateLimitedGet(
            url: URL(string: "https://musicbrainz.org/ws/2/release")!,
            queryItems: [
                URLQueryItem(name: "query", value: "release:\"\(album)\" artist:\"\(artist)\""),
                URLQueryItem(name: "fmt", value: "json"),
                URLQueryItem(name: "limit", value: "5"),
            ]
        )
    }

    public func releaseMetadata(mbid: String) async throws -> AlbumMetadataRecord? {
        let json = try await rateLimitedGet(
            url: URL(string: "https://musicbrainz.org/ws/2/release/\(mbid)")!,
            queryItems: [
                URLQueryItem(name: "fmt", value: "json"),
                URLQueryItem(name: "inc", value: "artists+labels"),
            ]
        )
        guard let data = json.first else { return nil }
        let title = data["title"] as? String ?? ""
        var artists: [String] = []
        if let credits = data["artist-credit"] as? [[String: Any]] {
            for credit in credits {
                if let artistDict = credit["artist"] as? [String: Any],
                   let name = artistDict["name"] as? String {
                    artists.append(name)
                }
            }
        }
        let artistName = artists.joined(separator: ", ")
        let date = data["date"] as? String ?? ""
        let year = Int(date.prefix(4)) ?? 0
        return AlbumMetadataRecord(
            title: title,
            artist: artistName.isEmpty ? "Unknown Artist" : artistName,
            year: year,
            mbid: mbid,
            trackCount: (data["track-count"] as? Int) ?? 0
        )
    }

    private func rateLimitedGet(url: URL, queryItems: [URLQueryItem]) async throws -> [[String: Any]] {
        await waitForRateLimit()
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        components.queryItems = queryItems
        var request = URLRequest(url: components.url!)
        request.setValue(userAgent, forHTTPHeaderField: "User-Agent")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else { return [] }
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [] }
        if let releases = object["releases"] as? [[String: Any]] {
            return releases
        }
        return [object]
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
