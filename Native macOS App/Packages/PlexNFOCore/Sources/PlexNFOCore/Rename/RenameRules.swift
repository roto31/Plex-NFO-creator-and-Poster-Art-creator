import Foundation

public enum RenameRules {
    public static let renameExtensions: Set<String> = [
        ".mkv", ".mp4", ".mov", ".avi", ".m4v", ".nfo", ".jpg", ".png", ".srt", ".sub",
    ]

    private static let qualityTagsPattern = #"""
    HD|1080p|1080i|720p|2160p|4K|UHD|
    Blu-?Ray|BluRay|BDRip|BRRip|
    WEB-?DL|WEBRip|HDTV|DVDRip|DVD|
    x264|x265|H\.?264|H\.?265|HEVC|AVC|
    AAC|AC3|DTS|DD5\.1|
    Unrated|Extended|Remastered|
    4K83|4K77|4K80|
    YTS|YTS\.MX|YIFY|RARBG
    """#.replacingOccurrences(of: "\n", with: "")

    private static let multipartPatterns: [NSRegularExpression] = [
        #"\bPart\s*\d+\b"#,
        #"-\s*part\s*\d+"#,
        #"\(\s*part\s*\d+\s*\)"#,
        #"\bDisc\s*\d+\b"#,
        #"\bDisk\s*\d+\b"#,
        #"\bD\d+\b"#,
        #"\b\d+\s*of\s*\d+\b"#,
        #"\bpt\s*\d+\b"#,
        #"\bVolume\s*\d+\b"#,
        #"\bVol\s*\.?\s*\d+\b"#,
        #"\bEpisode\s*\d+\b"#,
        #"\bChapter\s*\d+\b"#,
    ].compactMap { try? NSRegularExpression(pattern: $0, options: [.caseInsensitive]) }

    public static func cleanName(_ name: String) -> String {
        let url = URL(fileURLWithPath: name)
        let ext = url.pathExtension
        let hasExt = !ext.isEmpty && renameExtensions.contains(".\(ext.lowercased())")
        var working = hasExt ? url.deletingPathExtension().lastPathComponent : name

        if let regex = try? NSRegularExpression(pattern: #"^\d{1,2}\s+(?=[A-Za-z])"#) {
            working = regex.stringByReplacingMatches(
                in: working,
                range: NSRange(working.startIndex..., in: working),
                withTemplate: ""
            ).trimmingCharacters(in: .whitespaces)
        }

        let qualityRegex = try? NSRegularExpression(
            pattern: #"\s*[\(\[](\#(qualityTagsPattern))[\)\]]"#,
            options: [.caseInsensitive]
        )
        if let qualityRegex {
            working = qualityRegex.stringByReplacingMatches(
                in: working,
                range: NSRange(working.startIndex..., in: working),
                withTemplate: ""
            ).trimmingCharacters(in: .whitespaces)
        }

        if let bracketRegex = try? NSRegularExpression(pattern: #"\s*\[.*?\]\s*"#) {
            working = bracketRegex.stringByReplacingMatches(
                in: working,
                range: NSRange(working.startIndex..., in: working),
                withTemplate: ""
            ).trimmingCharacters(in: .whitespaces)
        }

        working = working.trimmingCharacters(in: CharacterSet(charactersIn: "_-. "))
        working = working.replacingOccurrences(of: "_", with: " ").trimmingCharacters(in: .whitespaces)
        if let spaceRegex = try? NSRegularExpression(pattern: #"\s{2,}"#) {
            working = spaceRegex.stringByReplacingMatches(
                in: working,
                range: NSRange(working.startIndex..., in: working),
                withTemplate: " "
            ).trimmingCharacters(in: .whitespaces)
        }

        return hasExt ? "\(working).\(ext)" : working
    }

    public static func isMultipart(_ name: String) -> Bool {
        let range = NSRange(name.startIndex..., in: name)
        return multipartPatterns.contains { $0.firstMatch(in: name, range: range) != nil }
    }

    public static func shouldRename(original: String, cleaned: String) -> Bool {
        original != cleaned
    }
}
