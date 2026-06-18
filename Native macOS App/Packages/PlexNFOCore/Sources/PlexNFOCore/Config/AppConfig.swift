import Foundation

public struct AppConfig: Codable, Sendable, Equatable {
    public var libraryPaths: LibraryPathsConfig
    public var plexURL: String
    public var firstLaunchCompleted: Bool
    public var dryRunByDefault: Bool
    public var metadataSettings: MetadataGeneratorSettings

    public init(
        libraryPaths: LibraryPathsConfig = .default,
        plexURL: String = "http://localhost:32400",
        firstLaunchCompleted: Bool = false,
        dryRunByDefault: Bool = true,
        metadataSettings: MetadataGeneratorSettings = .default
    ) {
        self.libraryPaths = libraryPaths
        self.plexURL = plexURL
        self.firstLaunchCompleted = firstLaunchCompleted
        self.dryRunByDefault = dryRunByDefault
        self.metadataSettings = metadataSettings
    }

    public static let `default` = AppConfig()
}
