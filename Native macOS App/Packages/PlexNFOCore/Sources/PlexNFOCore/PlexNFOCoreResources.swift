import Foundation

private final class PlexNFOCoreBundleAnchor: NSObject {}

public enum PlexNFOCoreResources {
    public static var bundle: Bundle {
        Bundle(for: PlexNFOCoreBundleAnchor.self)
    }
}
