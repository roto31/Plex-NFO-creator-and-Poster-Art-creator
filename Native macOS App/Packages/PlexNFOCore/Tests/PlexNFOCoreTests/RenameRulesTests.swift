import XCTest
@testable import PlexNFOCore

final class RenameRulesTests: XCTestCase {
    func testCleanNameStripsLeadingNumber() {
        XCTAssertEqual(RenameRules.cleanName("01 The Hangover"), "The Hangover")
    }

    func testCleanNamePreservesYear() {
        XCTAssertEqual(RenameRules.cleanName("The Hangover (2009)"), "The Hangover (2009)")
    }

    func testCleanNameStripsQualityTags() {
        XCTAssertEqual(RenameRules.cleanName("Inception (2010) [1080p]"), "Inception (2010)")
    }

    func testCleanNameUnderscores() {
        XCTAssertEqual(RenameRules.cleanName("The_Dark_Knight"), "The Dark Knight")
    }

    func testCleanNameWithExtension() {
        XCTAssertEqual(RenameRules.cleanName("01 Movie (2020) [1080p].mkv"), "Movie (2020).mkv")
    }

    func testDoesNotStripThreeDigitPrefix() {
        XCTAssertEqual(RenameRules.cleanName("127 Hours"), "127 Hours")
    }

    func testIsMultipart() {
        XCTAssertTrue(RenameRules.isMultipart("Movie Part 2"))
        XCTAssertTrue(RenameRules.isMultipart("Movie - part 1"))
        XCTAssertTrue(RenameRules.isMultipart("Movie Disc 1"))
        XCTAssertFalse(RenameRules.isMultipart("The Matrix"))
    }
}
