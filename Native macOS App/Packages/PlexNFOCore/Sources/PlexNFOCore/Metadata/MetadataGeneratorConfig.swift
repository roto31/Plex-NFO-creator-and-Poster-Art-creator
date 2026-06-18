import Foundation

/// Bridges `AppConfig` + Keychain secrets to metadata-generator runtime settings.
public enum MetadataGeneratorConfig {
    public static func resolveRoots(from paths: LibraryPathsConfig) -> (tv: [String], movies: [String], music: [String]) {
        let tv = paths.tvLibraryRoots + (paths.tvLibraryRoot.isEmpty ? [] : [paths.tvLibraryRoot])
        let movies = paths.moviesLibraryRoots + (paths.moviesLibraryRoot.isEmpty ? [] : [paths.moviesLibraryRoot])
        let music = paths.musicLibraryRoots + (paths.musicLibraryRoot.isEmpty ? [] : [paths.musicLibraryRoot])
        return (tv, movies, music)
    }

    public static func defaultCacheDirectory() -> String {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Caches/PlexNFOCreator/metadata", isDirectory: true)
            .path
    }

    public static func defaultLogDirectory() -> String {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/PlexNFOCreator", isDirectory: true)
            .path
    }

    /// Parse legacy Python JSON config (`plex-metadata-generator.conf`) for migration/import.
    public static func importLegacyJSON(_ data: Data) throws -> (settings: MetadataGeneratorSettings, libraryPaths: LibraryPathsConfig) {
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw URLError(.cannotParseResponse)
        }
        var paths = LibraryPathsConfig()
        if let tv = json["tv_library_root"] as? String { paths.tvLibraryRoot = tv }
        if let movies = json["movies_library_root"] as? String { paths.moviesLibraryRoot = movies }
        if let music = json["music_library_root"] as? String { paths.musicLibraryRoot = music }
        if let tvList = json["tv_library_roots"] as? [String] { paths.tvLibraryRoots = tvList }
        if let movieList = json["movies_library_roots"] as? [String] { paths.moviesLibraryRoots = movieList }
        if let musicList = json["music_library_roots"] as? [String] { paths.musicLibraryRoots = musicList }

        var settings = MetadataGeneratorSettings.default
        if let tunarr = json["tunarr"] as? [String: Any], let db = tunarr["db_path"] as? String {
            settings.tunarrDBPath = db
        }
        if let cache = json["cache_dir"] as? String { settings.cacheDirectory = cache }
        if let plex = json["plex"] as? [String: Any] {
            settings.plexTVLibraryKey = String(describing: plex["tv_library_key"] ?? plex["library_key"] ?? "1")
            if let moviesKey = plex["movies_library_key"] { settings.plexMoviesLibraryKey = String(describing: moviesKey) }
            if let musicKey = plex["music_library_key"] { settings.plexMusicLibraryKey = String(describing: musicKey) }
        }
        if let contact = json["musicbrainz_contact"] as? String { settings.musicBrainzContact = contact }
        if let subtitles = json["subtitles"] as? [String: Any] {
            settings.subtitlesEnabled = subtitles["enabled"] as? Bool ?? false
        }
        if let mk = json["apple_musickit"] as? [String: Any] {
            settings.appleMusicKit = AppleMusicKitConfig(
                enabled: mk["enabled"] as? Bool ?? false,
                teamID: mk["team_id"] as? String ?? "",
                keyID: mk["key_id"] as? String ?? "",
                privateKeyPath: mk["private_key_path"] as? String ?? "",
                storefront: mk["storefront"] as? String ?? "us"
            )
        }
        if let scheduling = json["scheduling"] as? [String: Any] {
            var hour = 2
            var minute = 0
            if let daily = scheduling["daily_time"] as? String,
               let parsed = MetadataSchedulingConfig.parseDailyTime(daily) {
                hour = parsed.hour
                minute = parsed.minute
            }
            settings.scheduling = MetadataSchedulingConfig(
                enabled: scheduling["enabled"] as? Bool ?? false,
                hour: hour,
                minute: minute
            )
        }
        return (settings, paths)
    }
}
