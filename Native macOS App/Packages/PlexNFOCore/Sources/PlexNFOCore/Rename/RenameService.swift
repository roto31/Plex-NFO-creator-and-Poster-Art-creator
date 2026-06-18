import Foundation

public struct RenamePreviewItem: Sendable, Identifiable {
    public let id = UUID()
    public let originalPath: String
    public let proposedPath: String
    public let skippedMultipart: Bool

    public init(originalPath: String, proposedPath: String, skippedMultipart: Bool) {
        self.originalPath = originalPath
        self.proposedPath = proposedPath
        self.skippedMultipart = skippedMultipart
    }
}

public struct RenameService: Sendable {
    public init() {}

    public func preview(root: URL, dryRun: Bool = true) -> [RenamePreviewItem] {
        let fileManager = FileManager.default
        guard let entries = try? fileManager.contentsOfDirectory(
            at: root,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        var items: [RenamePreviewItem] = []
        for folder in entries {
            var isDir: ObjCBool = false
            guard fileManager.fileExists(atPath: folder.path, isDirectory: &isDir), isDir.boolValue else {
                continue
            }
            let folderName = folder.lastPathComponent
            if RenameRules.isMultipart(folderName) {
                items.append(RenamePreviewItem(
                    originalPath: folder.path,
                    proposedPath: folder.path,
                    skippedMultipart: true
                ))
                continue
            }
            let cleanedFolder = RenameRules.cleanName(folderName)
            if RenameRules.shouldRename(original: folderName, cleaned: cleanedFolder) {
                items.append(RenamePreviewItem(
                    originalPath: folder.path,
                    proposedPath: folder.deletingLastPathComponent()
                        .appendingPathComponent(cleanedFolder).path,
                    skippedMultipart: false
                ))
            }
        }
        _ = dryRun
        return items
    }
}
