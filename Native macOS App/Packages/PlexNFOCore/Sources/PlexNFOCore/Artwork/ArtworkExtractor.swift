import Foundation

public struct ArtworkExtractionRequest: Sendable {
    public let mediaFile: URL
    public let outputImage: URL
    public let strategy: Int

    public init(mediaFile: URL, outputImage: URL, strategy: Int = 1) {
        self.mediaFile = mediaFile
        self.outputImage = outputImage
        self.strategy = strategy
    }
}

public struct ArtworkExtractor: Sendable {
  public init() {}

  public func extract(request: ArtworkExtractionRequest, ffmpegURL: URL) async throws {
    guard request.strategy == 1 else {
      throw NSError(domain: "ArtworkExtractor", code: 1, userInfo: [
        NSLocalizedDescriptionKey: "Only strategy 1 is implemented in foundation build",
      ])
    }
    let process = Process()
    process.executableURL = ffmpegURL
    process.arguments = [
      "-y", "-i", request.mediaFile.path,
      "-map", "0:v:0", "-frames:v", "1",
      request.outputImage.path,
    ]
    try process.run()
    process.waitUntilExit()
    guard process.terminationStatus == 0 else {
      throw NSError(domain: "ArtworkExtractor", code: 2, userInfo: [
        NSLocalizedDescriptionKey: "ffmpeg exited with status \(process.terminationStatus)",
      ])
    }
  }
}
