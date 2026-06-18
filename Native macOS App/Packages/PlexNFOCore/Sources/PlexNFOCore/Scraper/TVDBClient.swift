import Foundation

public struct TVDBSearchResult: Codable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let year: String?
}

public struct TVDBClient: Sendable {
    private let apiKey: String
    private let session: URLSession
    private let rateLimiter: RateLimiter
    private var bearerToken: String?

    public init(apiKey: String, session: URLSession = .shared) {
        self.apiKey = apiKey
        self.session = session
        self.rateLimiter = RateLimiter(requestsPerSecond: 2)
    }

    public mutating func login() async throws {
        await rateLimiter.waitIfNeeded()
        var request = URLRequest(url: URL(string: "https://api4.thetvdb.com/v4/login")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["apikey": apiKey])
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw URLError(.userAuthenticationRequired)
        }
        struct TokenPayload: Decodable { struct DataBlock: Decodable { let token: String }; let data: DataBlock }
        bearerToken = try JSONDecoder().decode(TokenPayload.self, from: data).data.token
    }

    public mutating func searchSeries(query: String) async throws -> [TVDBSearchResult] {
        if bearerToken == nil { try await login() }
        await rateLimiter.waitIfNeeded()
        var components = URLComponents(string: "https://api4.thetvdb.com/v4/search")!
        components.queryItems = [URLQueryItem(name: "query", value: query)]
        var request = URLRequest(url: components.url!)
        request.setValue("Bearer \(bearerToken ?? "")", forHTTPHeaderField: "Authorization")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else { return [] }
        struct Payload: Decodable {
            struct Item: Decodable {
                let id: String
                let name: String
                let year: String?
            }
            let data: [Item]
        }
        return try JSONDecoder().decode(Payload.self, from: data).data.map {
            TVDBSearchResult(id: $0.id, name: $0.name, year: $0.year)
        }
    }
}
