import XCTest
@testable import PlexNFOCore

final class LibraryWriteProbeTests: XCTestCase {
    func testWriteProbeInTemporaryDirectory() {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        XCTAssertTrue(LibraryWriteProbe.checkWritePermission(at: dir.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: dir.appendingPathComponent(LibraryWriteProbe.probeFileName).path))
        try? FileManager.default.removeItem(at: dir)
    }
}
