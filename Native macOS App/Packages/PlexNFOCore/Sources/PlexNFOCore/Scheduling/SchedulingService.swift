import Foundation

public struct LaunchdScheduleConfig: Codable, Sendable, Equatable {
    public var enabled: Bool
    public var label: String
    public var hour: Int
    public var minute: Int

    public init(
        enabled: Bool = false,
        label: String = LaunchAgentScheduler.label,
        hour: Int = 3,
        minute: Int = 0
    ) {
        self.enabled = enabled
        self.label = label
        self.hour = hour
        self.minute = minute
    }

    public init(from scheduling: MetadataSchedulingConfig) {
        self.enabled = scheduling.enabled
        self.label = LaunchAgentScheduler.label
        self.hour = scheduling.hour
        self.minute = scheduling.minute
    }
}

public enum SchedulingService {
    public static func plistDictionary(config: LaunchdScheduleConfig, executablePath: String, logDirectory: String) -> [String: Any] {
        [
            "Label": config.label,
            "ProgramArguments": [executablePath, "--metadata-scheduled"],
            "StartCalendarInterval": [
                "Hour": config.hour,
                "Minute": config.minute,
            ],
            "RunAtLoad": false,
            "StandardOutPath": "\(logDirectory)/metadata-scheduler.log",
            "StandardErrorPath": "\(logDirectory)/metadata-scheduler-error.log",
            "ProcessType": "Background",
            "ThrottleInterval": 60,
        ]
    }

    public static func plistContent(config: LaunchdScheduleConfig, executablePath: String, logDirectory: String) -> String {
        let dict = plistDictionary(config: config, executablePath: executablePath, logDirectory: logDirectory)
        let data = (try? PropertyListSerialization.data(fromPropertyList: dict, format: .xml, options: 0)) ?? Data()
        return String(data: data, encoding: .utf8) ?? ""
    }

    public static func agentPath(for label: String) -> URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/LaunchAgents/\(label).plist")
    }
}
