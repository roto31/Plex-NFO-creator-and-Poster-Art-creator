import Foundation

public struct TMDBSearchResult: Codable, Sendable, Identifiable {
    public let id: Int
    public let title: String?
    public let name: String?
    public let releaseDate: String?
    public let firstAirDate: String?

    public var displayTitle: String { title ?? name ?? "Unknown" }

    enum CodingKeys: String, CodingKey {
        case id, title, name
        case releaseDate = "release_date"
        case firstAirDate = "first_air_date"
    }
}

public struct TMDBClient: Sendable {
    private let apiKey: String
    private let session: URLSession
    private let rateLimiter: RateLimiter

    public init(apiKey: String, session: URLSession = .shared) {
        self.apiKey = apiKey
        self.session = session
        self.rateLimiter = RateLimiter(requestsPerSecond: 4)
    }

    public func searchMovie(query: String) async throws -> [TMDBSearchResult] {
        await rateLimiter.waitIfNeeded()
        var components = URLComponents(string: "https://api.themoviedb.org/3/search/movie")!
        components.queryItems = [
            URLQueryItem(name: "api_key", value: apiKey),
            URLQueryItem(name: "query", value: query),
        ]
        guard let url = components.url else { return [] }
        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else { return [] }
        struct Payload: Decodable { let results: [TMDBSearchResult] }
        return try JSONDecoder().decode(Payload.self, from: data).results
    }
}
