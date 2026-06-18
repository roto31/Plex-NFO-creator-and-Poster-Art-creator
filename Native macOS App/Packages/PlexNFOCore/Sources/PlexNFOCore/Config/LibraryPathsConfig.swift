import Foundation

public struct LibraryPathsConfig: Codable, Sendable, Equatable {
    public var moviesLibraryRoots: [String]
    public var tvLibraryRoots: [String]
    public var musicLibraryRoots: [String]
    public var moviesLibraryRoot: String
    public var tvLibraryRoot: String
    public var musicLibraryRoot: String

    public init(
        moviesLibraryRoots: [String] = [],
        tvLibraryRoots: [String] = [],
        musicLibraryRoots: [String] = [],
        moviesLibraryRoot: String = "",
        tvLibraryRoot: String = "",
        musicLibraryRoot: String = ""
    ) {
        self.moviesLibraryRoots = moviesLibraryRoots
        self.tvLibraryRoots = tvLibraryRoots
        self.musicLibraryRoots = musicLibraryRoots
        self.moviesLibraryRoot = moviesLibraryRoot
        self.tvLibraryRoot = tvLibraryRoot
        self.musicLibraryRoot = musicLibraryRoot
    }

    public static let `default` = LibraryPathsConfig()
}
