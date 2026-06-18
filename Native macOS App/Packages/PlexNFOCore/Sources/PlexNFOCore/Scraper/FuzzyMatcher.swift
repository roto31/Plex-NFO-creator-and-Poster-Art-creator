import Foundation

public enum FuzzyMatcher {
    public static func variants(for title: String) -> [String] {
        var seen = Set<String>()
        var results: [String] = []

        func add(_ value: String) {
            let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty, !seen.contains(trimmed) else { return }
            seen.insert(trimmed)
            results.append(trimmed)
        }

        add(title)

        let punctuationStripped = title
            .replacingOccurrences(of: "'", with: " ")
            .replacingOccurrences(of: ",", with: " ")
            .replacingOccurrences(of: ":", with: " ")
            .replacingOccurrences(of: ".", with: " ")
            .replacingOccurrences(of: "-", with: " ")
            .replacingOccurrences(of: "  ", with: " ")
        add(punctuationStripped)

        if let articleRegex = try? NSRegularExpression(pattern: #"^(The|A|An)\s+"#, options: .caseInsensitive) {
            let range = NSRange(title.startIndex..., in: title)
            let withoutArticle = articleRegex.stringByReplacingMatches(in: title, range: range, withTemplate: "")
            add(withoutArticle)
        }

        if let trailingArticle = try? NSRegularExpression(pattern: #"^(.*),\s*(The|A|An)$"#, options: .caseInsensitive) {
            let range = NSRange(title.startIndex..., in: title)
            if let match = trailingArticle.firstMatch(in: title, range: range),
               match.numberOfRanges >= 3,
               let titleRange = Range(match.range(at: 1), in: title),
               let articleRange = Range(match.range(at: 2), in: title) {
                add("\(title[articleRange]) \(title[titleRange])")
            }
        }

        if let split = title.split(separator: " - ", maxSplits: 1).first {
            add(String(split))
        }
        if let split = title.split(separator: ": ", maxSplits: 1).first {
            add(String(split))
        }

        add(asciiFold(title))
        add(asciiFold(punctuationStripped))
        return results
    }

    private static func asciiFold(_ text: String) -> String {
        text.folding(options: [.diacriticInsensitive, .widthInsensitive], locale: .current)
            .unicodeScalars
            .filter { $0.isASCII }
            .map(String.init)
            .joined()
    }
}
