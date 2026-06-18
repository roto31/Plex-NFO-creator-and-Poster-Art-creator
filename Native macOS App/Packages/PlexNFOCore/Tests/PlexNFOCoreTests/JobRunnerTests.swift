import XCTest
@testable import PlexNFOCore

final class JobRunnerTests: XCTestCase {
    func testCancellationYieldsErrorEvent() async {
        let runner = JobRunner()
        let stream = await runner.run(kind: .preflight) {
            try await Task.sleep(nanoseconds: 500_000_000)
            return "should not finish"
        }

        let consumeTask = Task {
            var events: [JobEvent] = []
            for await event in stream {
                events.append(event)
            }
            return events
        }

        try? await Task.sleep(nanoseconds: 20_000_000)
        await runner.cancel()
        let events = await consumeTask.value

        XCTAssertTrue(events.contains(where: { event in
            if case .error("Cancelled") = event { return true }
            return false
        }))
        let stillRunning = await runner.isRunning
        XCTAssertFalse(stillRunning)
    }

    func testSuccessfulRunCompletes() async {
        let runner = JobRunner()
        let stream = await runner.run(kind: .rename) {
            "done"
        }

        var lastComplete: String?
        for await event in stream {
            if case .complete(let message) = event {
                lastComplete = message
            }
        }

        XCTAssertEqual(lastComplete, "done")
        let stillRunning = await runner.isRunning
        XCTAssertFalse(stillRunning)
    }
}
