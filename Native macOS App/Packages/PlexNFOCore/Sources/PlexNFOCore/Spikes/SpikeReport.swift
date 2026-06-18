import Foundation

public enum SpikeVerdict: String, Sendable {
    case go = "GO"
    case noGo = "NO-GO"
}

public struct SpikeReport: Sendable {
    public let nfoParityPassed: Bool
    public let ffmpegAvailable: Bool
    public let notes: [String]

    public init(nfoParityPassed: Bool, ffmpegAvailable: Bool, notes: [String] = []) {
        self.nfoParityPassed = nfoParityPassed
        self.ffmpegAvailable = ffmpegAvailable
        self.notes = notes
    }

    public var nfoVerdict: SpikeVerdict { nfoParityPassed ? .go : .noGo }
    public var ffmpegVerdict: SpikeVerdict { ffmpegAvailable ? .go : .noGo }

    public var overallVerdict: SpikeVerdict {
        nfoParityPassed ? .go : .noGo
    }

    public static func evaluate(sampleNFO: String, expectedContains: [String], bundle: Bundle = PlexNFOCoreResources.bundle) -> SpikeReport {
        let parity = expectedContains.allSatisfy { sampleNFO.contains($0) }
        let ffmpeg = FFmpegLocator.isAvailable(bundle: bundle)
        var notes: [String] = []
        notes.append("NFO parity: \(parity ? "pass" : "fail")")
        notes.append("ffmpeg: \(ffmpeg ? "available" : "not bundled yet")")
        return SpikeReport(nfoParityPassed: parity, ffmpegAvailable: ffmpeg, notes: notes)
    }
}
