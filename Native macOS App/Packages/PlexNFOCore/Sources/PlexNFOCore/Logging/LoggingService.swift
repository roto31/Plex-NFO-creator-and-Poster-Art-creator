import Foundation
import os

public enum LogCategory: String, Sendable {
    case general
    case rename
    case scraper
    case artwork
    case metadata
    case health
    case preflight
}

public final class LoggingService: @unchecked Sendable {
    public static let subsystem = "com.roto31.PlexNFOCreator"

    private var loggers: [LogCategory: Logger] = [:]
    private let lock = NSLock()

    public init() {}

    public func logger(for category: LogCategory) -> Logger {
        lock.lock()
        defer { lock.unlock() }
        if let existing = loggers[category] {
            return existing
        }
        let logger = Logger(subsystem: Self.subsystem, category: category.rawValue)
        loggers[category] = logger
        return logger
    }

    public func info(_ message: String, category: LogCategory = .general) {
        logger(for: category).info("\(message, privacy: .public)")
    }

    public func error(_ message: String, category: LogCategory = .general) {
        logger(for: category).error("\(message, privacy: .public)")
    }
}
