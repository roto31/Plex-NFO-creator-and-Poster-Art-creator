import Foundation

public enum JobEvent: Sendable {
    case log(String)
    case progress(current: Int, total: Int, message: String)
    case complete(String)
    case error(String)
}

public enum JobKind: String, Sendable {
    case rename
    case scraper
    case artwork
    case metadata
    case health
    case preflight
}
