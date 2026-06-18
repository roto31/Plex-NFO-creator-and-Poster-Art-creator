import Foundation

public enum NFOPrettyXMLError: Error, LocalizedError {
    case parseFailed
    case writeFailed

    public var errorDescription: String? {
        switch self {
        case .parseFailed: return "Failed to parse NFO XML"
        case .writeFailed: return "Failed to write pretty NFO XML"
        }
    }
}

/// Strategy-1 spike: pretty-print NFO XML using Foundation XMLDocument.
public enum NFOPrettyXML {
    public static func prettyPrint(_ xml: String) throws -> String {
        guard let data = xml.data(using: .utf8) else { throw NFOPrettyXMLError.parseFailed }
        let doc = try XMLDocument(data: data, options: [.nodePreserveWhitespace, .nodeCompactEmptyElement])
        doc.characterEncoding = "UTF-8"
        guard let output = doc.xmlString(options: [.nodePrettyPrint]).data(using: .utf8) else {
            throw NFOPrettyXMLError.writeFailed
        }
        return String(decoding: output, as: UTF8.self)
    }

    public static func prettyPrintFile(at url: URL) throws -> String {
        let raw = try String(contentsOf: url, encoding: .utf8)
        return try prettyPrint(raw)
    }
}
