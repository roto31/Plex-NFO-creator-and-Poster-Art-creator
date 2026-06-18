// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "PlexNFOCreator",
    platforms: [.macOS(.v14)],
    products: [
        .library(name: "PlexNFOCore", targets: ["PlexNFOCore"]),
        .executable(name: "PlexNFOCreator", targets: ["PlexNFOCreator"]),
    ],
    targets: [
        .target(
            name: "PlexNFOCore",
            path: "Packages/PlexNFOCore/Sources/PlexNFOCore",
            exclude: ["Resources"],
            resources: [.process("Resources")]
        ),
        .executableTarget(
            name: "PlexNFOCreator",
            dependencies: ["PlexNFOCore"],
            path: "PlexNFOCreator/Sources/PlexNFOCreator"
        ),
        .testTarget(
            name: "PlexNFOCoreTests",
            dependencies: ["PlexNFOCore"],
            path: "Packages/PlexNFOCore/Tests/PlexNFOCoreTests",
            resources: [.copy("Fixtures")]
        ),
    ]
)
