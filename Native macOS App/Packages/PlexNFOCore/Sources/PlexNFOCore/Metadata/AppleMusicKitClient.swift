import Foundation
import CryptoKit

public enum AppleMusicKitTokenGenerator {
    public struct Credentials: Sendable {
        public let teamID: String
        public let keyID: String
        public let privateKeyPEM: String

        public init(teamID: String, keyID: String, privateKeyPEM: String) {
            self.teamID = teamID
            self.keyID = keyID
            self.privateKeyPEM = privateKeyPEM
        }
    }

    public static func makeDeveloperToken(credentials: Credentials, now: Date = Date()) throws -> String {
        let headerData = try JSONSerialization.data(withJSONObject: ["alg": "ES256", "kid": credentials.keyID])
        let iat = Int(now.timeIntervalSince1970)
        let exp = iat + 15_777_000
        let payloadData = try JSONSerialization.data(withJSONObject: [
            "iss": credentials.teamID,
            "iat": iat,
            "exp": exp,
        ])
        let header = base64URLEncode(headerData)
        let payload = base64URLEncode(payloadData)
        let signingInput = Data("\(header).\(payload)".utf8)
        let key = try loadPrivateKey(pem: credentials.privateKeyPEM)
        let signature = try key.signature(for: signingInput)
        let rawSignature = signature.rawRepresentation
        return "\(header).\(payload).\(base64URLEncode(rawSignature))"
    }

    private static func loadPrivateKey(pem: String) throws -> P256.Signing.PrivateKey {
        let lines = pem
            .components(separatedBy: .newlines)
            .filter { !$0.hasPrefix("-----") && !$0.isEmpty }
            .joined()
        guard let der = Data(base64Encoded: lines) else {
            throw URLError(.cannotDecodeContentData)
        }
        return try P256.Signing.PrivateKey(derRepresentation: der)
    }

    private static func base64URLEncode(_ data: Data) -> String {
        data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

public final class AppleMusicKitClient: @unchecked Sendable {
    private let credentials: AppleMusicKitTokenGenerator.Credentials
    private let storefront: String
    private let session: URLSession
    private let tokenLock = NSLock()
    private var cachedToken: String?
    private var tokenExpiry: TimeInterval = 0

    public init(credentials: AppleMusicKitTokenGenerator.Credentials, storefront: String = "us", session: URLSession = .shared) {
        self.credentials = credentials
        self.storefront = storefront
        self.session = session
    }

    public func searchAlbum(term: String) async throws -> [[String: Any]] {
        guard let token = try currentToken() else { return [] }
        var components = URLComponents(string: "https://api.music.apple.com/v1/catalog/\(storefront)/search")!
        components.queryItems = [
            URLQueryItem(name: "term", value: term),
            URLQueryItem(name: "types", value: "albums"),
            URLQueryItem(name: "limit", value: "5"),
        ]
        var request = URLRequest(url: components.url!)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else { return [] }
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let results = json["results"] as? [String: Any],
              let albums = results["albums"] as? [String: Any],
              let items = albums["data"] as? [[String: Any]] else { return [] }
        return items
    }

    public func albumMetadata(from record: [String: Any]) -> AlbumMetadataRecord? {
        guard let attributes = record["attributes"] as? [String: Any] else { return nil }
        let title = attributes["name"] as? String ?? ""
        let artist = attributes["artistName"] as? String ?? "Unknown Artist"
        let releaseDate = attributes["releaseDate"] as? String ?? ""
        let year = Int(releaseDate.prefix(4)) ?? 0
        let artworkTemplate = (attributes["artwork"] as? [String: Any])?["url"] as? String
        let coverURL = artworkTemplate?
            .replacingOccurrences(of: "{w}", with: "3000")
            .replacingOccurrences(of: "{h}", with: "3000")
        return AlbumMetadataRecord(
            title: title,
            artist: artist,
            year: year,
            genres: (attributes["genreNames"] as? [String]) ?? [],
            appleID: record["id"] as? String,
            coverURL: coverURL,
            trackCount: attributes["trackCount"] as? Int ?? 0
        )
    }

    private func currentToken() throws -> String? {
        tokenLock.lock()
        let now = Date().timeIntervalSince1970
        if let token = cachedToken, now < tokenExpiry {
            tokenLock.unlock()
            return token
        }
        tokenLock.unlock()
        let token = try AppleMusicKitTokenGenerator.makeDeveloperToken(credentials: credentials)
        tokenLock.lock()
        cachedToken = token
        tokenExpiry = now + 15_776_940
        tokenLock.unlock()
        return token
    }
}
