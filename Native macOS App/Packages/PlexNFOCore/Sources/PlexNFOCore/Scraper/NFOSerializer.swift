import Foundation

public enum NFOSerializer {
  public static func prettyXML(from element: XMLElement) -> String {
    let doc = XMLDocument(rootElement: element)
    doc.version = "1.0"
    doc.characterEncoding = "utf-8"
    let data = doc.xmlData(options: [.nodePrettyPrint])
    var text = String(data: data, encoding: .utf8) ?? ""
    text = text.replacingOccurrences(of: #"<?xml version="1.0" encoding="utf-8"?>"#, with: "<?xml version='1.0' encoding='utf-8'?>")
    return text.trimmingCharacters(in: .newlines) + "\n"
  }

  public static func movieNFO(title: String, year: String?, tmdbID: String?, plot: String?) -> String {
    let root = XMLElement(name: "movie")
    appendChild(root, name: "title", value: title)
    if let year { appendChild(root, name: "year", value: year) }
    if let plot { appendChild(root, name: "plot", value: plot) }
    if let tmdbID {
      let uid = XMLElement(name: "uniqueid")
      if let typeAttr = XMLNode.attribute(withName: "type", stringValue: "tmdb") as? XMLNode {
        uid.addAttribute(typeAttr)
      }
      if let defaultAttr = XMLNode.attribute(withName: "default", stringValue: "true") as? XMLNode {
        uid.addAttribute(defaultAttr)
      }
      uid.stringValue = tmdbID
      root.addChild(uid)
    }
    return prettyXML(from: root)
  }

  private static func appendChild(_ parent: XMLElement, name: String, value: String) {
    let child = XMLElement(name: name)
    child.stringValue = value
    parent.addChild(child)
  }
}
