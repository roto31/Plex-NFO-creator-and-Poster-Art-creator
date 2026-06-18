import Foundation

public struct PlexClient: Sendable {
    private let baseURL: String
    private let token: String
    private let session: URLSession

    public init(baseURL: String, token: String, session: URLSession = .shared) {
        self.baseURL = baseURL.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        self.token = token
        self.session = session
    }

    public func connectivityCheck() async -> (ok: Bool, detail: String) {
        guard !token.isEmpty else {
            return (false, "Plex token not configured")
        }
        guard let url = URL(string: "\(baseURL)/library/sections?X-Plex-Token=\(token)") else {
            return (false, "Invalid Plex URL")
        }
        do {
            let (_, response) = try await session.data(from: url)
            guard let http = response as? HTTPURLResponse else {
                return (false, "No HTTP response")
            }
            return http.statusCode == 200
                ? (true, "Plex API reachable")
                : (false, "Plex API returned HTTP \(http.statusCode)")
        } catch {
            return (false, error.localizedDescription)
        }
    }

    public func refreshLibrary(sectionKey: String) async throws {
        guard !sectionKey.isEmpty, !token.isEmpty else { return }
        guard let url = URL(string: "\(baseURL)/library/sections/\(sectionKey)/refresh?X-Plex-Token=\(token)") else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
    }
}
