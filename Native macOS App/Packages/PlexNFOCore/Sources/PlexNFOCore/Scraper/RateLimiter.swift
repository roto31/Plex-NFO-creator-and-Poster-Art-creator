import Foundation

public actor RateLimiter {
    private let interval: TimeInterval
    private var lastFire: Date?

    public init(requestsPerSecond: Double) {
        interval = requestsPerSecond > 0 ? 1.0 / requestsPerSecond : 0
    }

    public func waitIfNeeded() async {
        guard interval > 0 else { return }
        if let lastFire {
            let elapsed = Date().timeIntervalSince(lastFire)
            if elapsed < interval {
                try? await Task.sleep(nanoseconds: UInt64((interval - elapsed) * 1_000_000_000))
            }
        }
        lastFire = Date()
    }
}
