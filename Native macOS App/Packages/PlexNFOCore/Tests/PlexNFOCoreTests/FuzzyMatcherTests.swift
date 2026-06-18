import XCTest
@testable import PlexNFOCore

final class FuzzyMatcherTests: XCTestCase {
    func testVariantsIncludeOriginal() {
        let variants = FuzzyMatcher.variants(for: "The Matrix")
        XCTAssertEqual(variants.first, "The Matrix")
        XCTAssertTrue(variants.contains("Matrix"))
    }

    func testTrailingArticle() {
        let variants = FuzzyMatcher.variants(for: "Matrix, The")
        XCTAssertTrue(variants.contains("The Matrix"))
    }

    func testSubtitleSplit() {
        let variants = FuzzyMatcher.variants(for: "Star Wars - A New Hope")
        XCTAssertTrue(variants.contains("Star Wars"))
    }
}
