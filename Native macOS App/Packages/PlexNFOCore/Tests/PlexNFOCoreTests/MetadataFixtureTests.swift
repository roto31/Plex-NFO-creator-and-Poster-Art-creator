import XCTest
@testable import PlexNFOCore

final class MetadataFixtureTests: XCTestCase {
    func testShowNFOMatchesMetadataGeneratorFixture() throws {
        let fixtureURL = Bundle.module.url(forResource: "mg-tvshow", withExtension: "nfo", subdirectory: "Fixtures")!
        let fixture = try String(contentsOf: fixtureURL, encoding: .utf8)
        let record = ShowMetadataRecord(
            title: "Fixture Show",
            year: 2020,
            plot: "Fixture plot",
            rating: 8.5,
            tvdbID: 80348,
            tmdbID: 1396,
            imdbID: "tt0903747",
            genres: ["Drama", "Crime"]
        )
        let generated = MetadataNFOGenerator.showNFO(record)
        for token in ["<title>Fixture Show</title>", "<year>2020</year>", "80348", "1396", "tt0903747", "Drama"] {
            XCTAssertTrue(generated.contains(token), "missing \(token)")
            XCTAssertTrue(fixture.contains(token), "fixture missing \(token)")
        }
    }

    func testMetadataGeneratorFixturesExist() throws {
        let names = ["mg-tvshow", "mg-episode", "mg-movie"]
        for name in names {
            let url = Bundle.module.url(forResource: name, withExtension: "nfo", subdirectory: "Fixtures")
            XCTAssertNotNil(url, "missing fixture \(name).nfo")
            let text = try String(contentsOf: url!, encoding: .utf8)
            XCTAssertTrue(text.contains("<?xml"))
        }
    }
}
