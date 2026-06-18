import Foundation

public enum ConfigStoreError: Error, Sendable {
    case directoryCreationFailed
    case writeFailed
    case readFailed
}

public final class ConfigStore: @unchecked Sendable {
    public static let appSupportFolderName = "PlexNFOCreator"
    public static let configFileName = "config.json"

    private let fileManager: FileManager
    private let configURL: URL
    private let lock = NSLock()

    public init(fileManager: FileManager = .default, configDirectory: URL? = nil) throws {
        self.fileManager = fileManager
        let directory: URL
        if let configDirectory {
            directory = configDirectory
        } else {
            guard let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
                throw ConfigStoreError.directoryCreationFailed
            }
            directory = appSupport.appendingPathComponent(Self.appSupportFolderName, isDirectory: true)
        }
        if !fileManager.fileExists(atPath: directory.path) {
            try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
        }
        configURL = directory.appendingPathComponent(Self.configFileName)
    }

    public var configFileURL: URL { configURL }

    public func load() throws -> AppConfig {
        lock.lock()
        defer { lock.unlock() }
        guard fileManager.fileExists(atPath: configURL.path) else {
            return .default
        }
        guard let data = try? Data(contentsOf: configURL) else {
            throw ConfigStoreError.readFailed
        }
        return try JSONDecoder().decode(AppConfig.self, from: data)
    }

    public func save(_ config: AppConfig) throws {
        lock.lock()
        defer { lock.unlock() }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(config)
        let tempURL = configURL.appendingPathExtension("tmp")
        do {
            try data.write(to: tempURL, options: .atomic)
            if fileManager.fileExists(atPath: configURL.path) {
                try fileManager.replaceItemAt(configURL, withItemAt: tempURL)
            } else {
                try fileManager.moveItem(at: tempURL, to: configURL)
            }
        } catch {
            try? fileManager.removeItem(at: tempURL)
            throw ConfigStoreError.writeFailed
        }
    }
}
