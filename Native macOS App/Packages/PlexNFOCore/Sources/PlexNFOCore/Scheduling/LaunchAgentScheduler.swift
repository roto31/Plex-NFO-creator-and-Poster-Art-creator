import Foundation

#if canImport(ServiceManagement)
import ServiceManagement
#endif

public struct LaunchAgentScheduler: Sendable {
    public static let label = "com.roto31.PlexNFOCreator.metadata"
    public static let plistFileName = "\(label).plist"

    public init() {}

    public static func plistURL() -> URL {
        SchedulingService.agentPath(for: label)
    }

    public func plistURL() -> URL { Self.plistURL() }

    public func generatePlist(executablePath: String, schedule: LaunchdScheduleConfig) -> Data {
        let logDir = MetadataGeneratorConfig.defaultLogDirectory()
        let dict = SchedulingService.plistDictionary(
            config: schedule,
            executablePath: executablePath,
            logDirectory: logDir
        )
        return (try? PropertyListSerialization.data(fromPropertyList: dict, format: .xml, options: 0)) ?? Data()
    }

    public func writePlist(executablePath: String, schedule: LaunchdScheduleConfig) throws {
        let url = Self.plistURL()
        let directory = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(
            atPath: MetadataGeneratorConfig.defaultLogDirectory(),
            withIntermediateDirectories: true
        )
        let data = generatePlist(executablePath: executablePath, schedule: schedule)
        let temp = url.appendingPathExtension("tmp")
        try data.write(to: temp, options: .atomic)
        if FileManager.default.fileExists(atPath: url.path) {
            try FileManager.default.replaceItemAt(url, withItemAt: temp)
        } else {
            try FileManager.default.moveItem(at: temp, to: url)
        }
    }

    public func removePlist() throws {
        let url = Self.plistURL()
        if FileManager.default.fileExists(atPath: url.path) {
            try FileManager.default.removeItem(at: url)
        }
    }

    @available(macOS 14.0, *)
    public func registerWithSMAppService() throws {
        #if canImport(ServiceManagement)
        let service = SMAppService.agent(plistName: Self.plistFileName)
        try service.register()
        #endif
    }

    @available(macOS 14.0, *)
    public func unregisterFromSMAppService() throws {
        #if canImport(ServiceManagement)
        let service = SMAppService.agent(plistName: Self.plistFileName)
        try service.unregister()
        #endif
    }

    @available(macOS 14.0, *)
    public static func smAppServiceStatus() -> String {
        #if canImport(ServiceManagement)
        switch SMAppService.agent(plistName: plistFileName).status {
        case .enabled: return "enabled"
        case .requiresApproval: return "requires approval"
        case .notRegistered: return "not registered"
        case .notFound: return "not found"
        @unknown default: return "unknown"
        }
        #else
        return "unavailable"
        #endif
    }
}

public enum DailySchedulingManager {
    public static func apply(
        enabled: Bool,
        schedule: MetadataSchedulingConfig,
        executablePath: String
    ) throws -> String {
        let scheduler = LaunchAgentScheduler()
        let launchdConfig = LaunchdScheduleConfig(from: schedule)
        if enabled {
            try scheduler.writePlist(executablePath: executablePath, schedule: launchdConfig)
            if #available(macOS 14.0, *) {
                do {
                    try scheduler.registerWithSMAppService()
                    return "Daily scheduling enabled via SMAppService at \(String(format: "%02d:%02d", schedule.hour, schedule.minute))"
                } catch {
                    return "SMAppService registration failed (\(error.localizedDescription)); launch agent plist written to \(scheduler.plistURL().path) — load manually with launchctl"
                }
            }
            return "Launch agent plist written to \(scheduler.plistURL().path) — load with: launchctl load \(scheduler.plistURL().path)"
        }
        try scheduler.removePlist()
        if #available(macOS 14.0, *) {
            try? scheduler.unregisterFromSMAppService()
        }
        return "Daily scheduling disabled"
    }
}
