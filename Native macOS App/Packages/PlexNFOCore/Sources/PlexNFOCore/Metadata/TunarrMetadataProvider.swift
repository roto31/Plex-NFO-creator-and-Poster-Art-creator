import Foundation
import SQLite3

public struct TunarrShowLookup: Sendable {
    public let title: String
    public let summary: String
    public let duration: Int?
    public let rating: Double?
}

public struct TunarrMetadataProvider: Sendable {
    private let dbPath: String

    public init(dbPath: String) {
        self.dbPath = dbPath
    }

    public var isAvailable: Bool {
        !dbPath.isEmpty && FileManager.default.fileExists(atPath: dbPath)
    }

    public func lookupShow(title: String) -> TunarrShowLookup? {
        guard isAvailable else { return nil }
        var db: OpaquePointer?
        guard sqlite3_open_v2(dbPath, &db, SQLITE_OPEN_READONLY, nil) == SQLITE_OK else {
            sqlite3_close(db)
            return nil
        }
        defer { sqlite3_close(db) }

        let sql = "SELECT title, summary, duration, rating FROM programs WHERE title LIKE ? LIMIT 1"
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else { return nil }
        defer { sqlite3_finalize(statement) }

        let pattern = "%\(title)%"
        sqlite3_bind_text(statement, 1, pattern, -1, unsafeBitCast(-1, to: sqlite3_destructor_type.self))

        guard sqlite3_step(statement) == SQLITE_ROW else { return nil }

        let titleText = columnText(statement, index: 0) ?? title
        let summary = columnText(statement, index: 1) ?? ""
        let duration = sqlite3_column_type(statement, 2) != SQLITE_NULL ? Int(sqlite3_column_int(statement, 2)) : nil
        let rating = sqlite3_column_type(statement, 3) != SQLITE_NULL ? sqlite3_column_double(statement, 3) : nil

        return TunarrShowLookup(title: titleText, summary: summary, duration: duration, rating: rating)
    }

    private func columnText(_ statement: OpaquePointer?, index: Int32) -> String? {
        guard let cString = sqlite3_column_text(statement, index) else { return nil }
        return String(cString: cString)
    }
}
