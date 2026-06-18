import Foundation

public struct MetadataSchedulingConfig: Codable, Sendable, Equatable {
    public var enabled: Bool
    public var hour: Int
    public var minute: Int

    public init(enabled: Bool = false, hour: Int = 2, minute: Int = 0) {
        self.enabled = enabled
        self.hour = hour
        self.minute = minute
    }

    public static func parseDailyTime(_ value: String) -> (hour: Int, minute: Int)? {
        let parts = value.split(separator: ":")
        guard parts.count == 2,
              let hour = Int(parts[0]),
              let minute = Int(parts[1]),
              (0...23).contains(hour),
              (0...59).contains(minute) else { return nil }
        return (hour, minute)
    }
}

public struct AppleMusicKitConfig: Codable, Sendable, Equatable {
    public var enabled: Bool
    public var teamID: String
    public var keyID: String
    public var privateKeyPath: String
    public var storefront: String

    public init(
        enabled: Bool = false,
        teamID: String = "",
        keyID: String = "",
        privateKeyPath: String = "",
        storefront: String = "us"
    ) {
        self.enabled = enabled
        self.teamID = teamID
        self.keyID = keyID
        self.privateKeyPath = privateKeyPath
        self.storefront = storefront
    }
}

public struct MetadataGeneratorSettings: Codable, Sendable, Equatable {
    public var tunarrDBPath: String
    public var cacheDirectory: String
    public var plexTVLibraryKey: String
    public var plexMoviesLibraryKey: String
    public var plexMusicLibraryKey: String
    public var musicBrainzContact: String
    public var appleMusicKit: AppleMusicKitConfig
    public var subtitlesEnabled: Bool
    public var scheduling: MetadataSchedulingConfig

    public init(
        tunarrDBPath: String = "",
        cacheDirectory: String = "",
        plexTVLibraryKey: String = "1",
        plexMoviesLibraryKey: String = "2",
        plexMusicLibraryKey: String = "3",
        musicBrainzContact: String = "",
        appleMusicKit: AppleMusicKitConfig = .init(),
        subtitlesEnabled: Bool = false,
        scheduling: MetadataSchedulingConfig = .init()
    ) {
        self.tunarrDBPath = tunarrDBPath
        self.cacheDirectory = cacheDirectory
        self.plexTVLibraryKey = plexTVLibraryKey
        self.plexMoviesLibraryKey = plexMoviesLibraryKey
        self.plexMusicLibraryKey = plexMusicLibraryKey
        self.musicBrainzContact = musicBrainzContact
        self.appleMusicKit = appleMusicKit
        self.subtitlesEnabled = subtitlesEnabled
        self.scheduling = scheduling
    }

    public static let `default` = MetadataGeneratorSettings()
}
