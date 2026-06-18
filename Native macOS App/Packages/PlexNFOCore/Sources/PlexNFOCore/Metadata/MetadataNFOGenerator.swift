import Foundation

public enum MetadataNFOGenerator {
    public static func showNFO(_ metadata: ShowMetadataRecord) -> String {
        let root = XMLElement(name: "tvshow")
        appendText(root, name: "title", value: metadata.title)
        appendText(root, name: "originaltitle", value: metadata.title)
        if metadata.year > 0 { appendText(root, name: "year", value: String(metadata.year)) }
        appendText(root, name: "plot", value: metadata.plot)
        appendText(root, name: "rating", value: String(metadata.rating))
        appendText(root, name: "runtime", value: String(metadata.runtime))
        appendText(root, name: "status", value: metadata.status)
        if let tvdbID = metadata.tvdbID {
            appendUniqueID(root, type: "tvdb", value: String(tvdbID), isDefault: true)
        }
        if let tmdbID = metadata.tmdbID {
            appendUniqueID(root, type: "tmdb", value: String(tmdbID), isDefault: metadata.tvdbID == nil)
        }
        if let imdbID = metadata.imdbID {
            appendUniqueID(root, type: "imdb", value: imdbID, isDefault: false)
        }
        for genre in metadata.genres {
            appendText(root, name: "genre", value: genre)
        }
        return NFOSerializer.prettyXML(from: root)
    }

    public static func albumNFO(_ metadata: AlbumMetadataRecord) -> String {
        let root = XMLElement(name: "album")
        appendText(root, name: "title", value: metadata.title)
        appendText(root, name: "artist", value: metadata.artist)
        if metadata.year > 0 { appendText(root, name: "year", value: String(metadata.year)) }
        if !metadata.plot.isEmpty { appendText(root, name: "review", value: metadata.plot) }
        for genre in metadata.genres {
            appendText(root, name: "genre", value: genre)
        }
        if let mbid = metadata.mbid {
            appendUniqueID(root, type: "musicbrainz", value: mbid, isDefault: true)
        }
        if let appleID = metadata.appleID {
            appendUniqueID(root, type: "apple", value: appleID, isDefault: metadata.mbid == nil)
        }
        return NFOSerializer.prettyXML(from: root)
    }

    private static func appendText(_ parent: XMLElement, name: String, value: String) {
        let child = XMLElement(name: name)
        child.stringValue = value
        parent.addChild(child)
    }

    private static func appendUniqueID(_ parent: XMLElement, type: String, value: String, isDefault: Bool) {
        let uid = XMLElement(name: "uniqueid")
        if let typeAttr = XMLNode.attribute(withName: "type", stringValue: type) as? XMLNode {
            uid.addAttribute(typeAttr)
        }
        if let defaultAttr = XMLNode.attribute(withName: "default", stringValue: isDefault ? "true" : "false") as? XMLNode {
            uid.addAttribute(defaultAttr)
        }
        uid.stringValue = value
        parent.addChild(uid)
    }
}
