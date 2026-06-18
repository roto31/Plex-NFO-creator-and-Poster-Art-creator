import Foundation

public struct ScraperService: Sendable {
    private let tmdbAPIKey: String
    private let tvdbAPIKey: String

    public init(tmdbAPIKey: String, tvdbAPIKey: String) {
        self.tmdbAPIKey = tmdbAPIKey
        self.tvdbAPIKey = tvdbAPIKey
    }

    public func generateMovieNFO(title: String, year: String?) async throws -> String {
        let client = TMDBClient(apiKey: tmdbAPIKey)
        var chosenID: String?
        for variant in FuzzyMatcher.variants(for: title) {
            let results = try await client.searchMovie(query: variant)
            if let first = results.first {
                chosenID = String(first.id)
                break
            }
        }
        return NFOSerializer.movieNFO(title: title, year: year, tmdbID: chosenID, plot: nil)
    }

    public func previewSearch(title: String) async throws -> [TMDBSearchResult] {
        let client = TMDBClient(apiKey: tmdbAPIKey)
        return try await client.searchMovie(query: title)
    }
}
