import Foundation
import PlexNFOCore

@MainActor
final class AppState: ObservableObject {
    @Published var config: AppConfig
    @Published var versionInfo: VersionInfo
    @Published var jobLog: [String] = []
    @Published var isJobRunning = false
    @Published var showProgressSheet = false
    @Published var showFirstLaunch = false

    let configStore: ConfigStore
    let keychain: KeychainStore
    let jobRunner: JobRunner
    let logging: LoggingService

    init() {
        versionInfo = VersionInfo()
        keychain = KeychainStore()
        jobRunner = JobRunner()
        logging = LoggingService()
        if let store = try? ConfigStore() {
            configStore = store
            config = (try? store.load()) ?? .default
        } else {
            configStore = try! ConfigStore(configDirectory: FileManager.default.temporaryDirectory)
            config = .default
        }
        showFirstLaunch = !config.firstLaunchCompleted
        handleCommandLineArgumentsIfNeeded()
    }

    func saveConfig() {
        try? configStore.save(config)
    }

    func runScheduledMetadataScan() {
        let options = MetadataGeneratorOptions(includeMusic: true, dryRun: false)
        let request = MetadataGeneratorRequest(options: options, config: config, settings: config.metadataSettings)
        let service = MetadataGeneratorService(keychain: keychain, logging: logging)
        runJob(kind: .metadata) {
            let summary = try await service.run(request: request)
            return summary.description
        }
    }

    func cancelJob() async {
        await jobRunner.cancel()
    }

    func runJob(kind: JobKind, operation: @escaping @Sendable () async throws -> String) {
        isJobRunning = true
        showProgressSheet = true
        jobLog = []
        Task {
            let stream = await jobRunner.run(kind: kind, operation: operation)
            for await event in stream {
                await MainActor.run {
                    switch event {
                    case .log(let message), .complete(let message):
                        jobLog.append(message)
                    case .progress(_, _, let message):
                        jobLog.append(message)
                    case .error(let message):
                        jobLog.append("ERROR: \(message)")
                    }
                }
            }
            await MainActor.run {
                isJobRunning = false
            }
        }
    }

    private func handleCommandLineArgumentsIfNeeded() {
        let args = CommandLine.arguments
        guard args.contains("--metadata-scheduled") else { return }
        runScheduledMetadataScan()
    }
}
