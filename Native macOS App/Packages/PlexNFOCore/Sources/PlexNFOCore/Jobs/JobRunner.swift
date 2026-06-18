import Foundation

public actor JobRunner {
    private var runningTask: Task<Void, Never>?

    public init() {}

    public var isRunning: Bool {
        runningTask != nil
    }

    public func run(
        kind: JobKind,
        operation: @escaping @Sendable () async throws -> String
    ) -> AsyncStream<JobEvent> {
        cancel()
        let (stream, continuation) = AsyncStream<JobEvent>.makeStream()
        continuation.yield(.log("Starting \(kind.rawValue) job"))
        let task = Task {
            do {
                try Task.checkCancellation()
                let result = try await operation()
                try Task.checkCancellation()
                continuation.yield(.complete(result))
            } catch is CancellationError {
                continuation.yield(.error("Cancelled"))
            } catch {
                continuation.yield(.error(error.localizedDescription))
            }
            continuation.finish()
            await clearTask()
        }
        runningTask = task
        return stream
    }

    public func cancel() {
        runningTask?.cancel()
        runningTask = nil
    }

    private func clearTask() {
        runningTask = nil
    }
}
