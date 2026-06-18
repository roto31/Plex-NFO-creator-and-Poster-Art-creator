import Foundation

public enum FFmpegLocator {
    public static let bundledRelativePath = "Resources/ffmpeg"

    public static func locate(bundle: Bundle = PlexNFOCoreResources.bundle) -> URL? {
        if let bundled = bundle.url(forResource: "ffmpeg", withExtension: nil, subdirectory: bundledRelativePath) {
            return bundled
        }
        if let bundled = bundle.url(forResource: "ffmpeg", withExtension: nil) {
            return bundled
        }
        let which = Process()
        which.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        which.arguments = ["ffmpeg"]
        let pipe = Pipe()
        which.standardOutput = pipe
        try? which.run()
        which.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        guard let path = String(data: data, encoding: .utf8)?
            .trimmingCharacters(in: .whitespacesAndNewlines),
              !path.isEmpty else {
            return nil
        }
        return URL(fileURLWithPath: path)
    }

    public static func isAvailable(bundle: Bundle = PlexNFOCoreResources.bundle) -> Bool {
        locate(bundle: bundle) != nil
    }
}
