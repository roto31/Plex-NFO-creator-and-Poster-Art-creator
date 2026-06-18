import Foundation

public struct BundleDataManifest: Codable, Sendable {
    public struct DataRevision: Codable, Sendable {
        public var ffmpeg: Int
    }

    public var dataRevision: DataRevision
}

public struct VersionInfo: Sendable {
    public let marketingVersion: String
    public let dataRevision: BundleDataManifest.DataRevision

    public init(bundle: Bundle = PlexNFOCoreResources.bundle) {
        marketingVersion = Self.loadText(named: "VERSION", bundle: bundle)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? "0.0.0"
        dataRevision = Self.loadManifest(bundle: bundle)?.dataRevision ?? .init(ffmpeg: 0)
    }

    public var displayString: String {
        "v\(marketingVersion) (ffmpeg data rev \(dataRevision.ffmpeg))"
    }

    private static func loadText(named name: String, bundle: Bundle) -> String? {
        guard let url = bundle.url(forResource: name, withExtension: nil) else { return nil }
        return try? String(contentsOf: url, encoding: .utf8)
    }

    private static func loadManifest(bundle: Bundle) -> BundleDataManifest? {
        guard let url = bundle.url(forResource: "BundleDataManifest", withExtension: "json") else {
            return nil
        }
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(BundleDataManifest.self, from: data)
    }
}
