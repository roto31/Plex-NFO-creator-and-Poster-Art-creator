import XCTest
@testable import PlexNFOCore

final class NFOSerializerTests: XCTestCase {
    func testMovieNFOPrettyXML() {
        let xml = NFOSerializer.movieNFO(title: "Inception", year: "2010", tmdbID: "27205", plot: "A thief who steals secrets.")
        XCTAssertTrue(xml.contains("<?xml version='1.0' encoding='utf-8'?>"))
        XCTAssertTrue(xml.contains("<title>Inception</title>"))
        XCTAssertTrue(xml.contains("<year>2010</year>"))
        XCTAssertTrue(xml.contains("<uniqueid type=\"tmdb\" default=\"true\">27205</uniqueid>"))
    }

    func testFixtureParity() throws {
        let fixtureURL = Bundle.module.url(forResource: "sample-movie", withExtension: "nfo", subdirectory: "Fixtures")!
        let fixture = try String(contentsOf: fixtureURL, encoding: .utf8)
        let generated = NFOSerializer.movieNFO(title: "Inception", year: "2010", tmdbID: "27205", plot: nil)
        let report = SpikeReport.evaluate(
            sampleNFO: generated,
            expectedContains: ["<title>Inception</title>", "<year>2010</year>", "27205"]
        )
        XCTAssertEqual(report.nfoVerdict, .go)
        XCTAssertTrue(fixture.contains("Inception"))
    }
}
