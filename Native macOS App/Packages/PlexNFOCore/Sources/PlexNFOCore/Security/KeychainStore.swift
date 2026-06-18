import Foundation
import Security

public enum KeychainStoreError: Error, Sendable {
    case encodingFailed
    case saveFailed(OSStatus)
    case readFailed(OSStatus)
    case deleteFailed(OSStatus)
    case notFound
}

public enum KeychainKey: String, CaseIterable, Sendable {
    case tmdbAPIKey = "tmdb.api_key"
    case tvdbAPIKey = "tvdb.api_key"
    case plexToken = "plex.token"
    case fanartAPIKey = "fanart.api_key"
    case appleMusicKitPrivateKey = "apple_musickit.private_key"
}

public final class KeychainStore: @unchecked Sendable {
    public static let serviceName = "com.roto31.PlexNFOCreator"

    private let service: String

    public init(service: String = KeychainStore.serviceName) {
        self.service = service
    }

    public func set(_ value: String, for key: KeychainKey) throws {
        guard let data = value.data(using: .utf8) else {
            throw KeychainStoreError.encodingFailed
        }
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock,
        ]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var addQuery = query
            addQuery[kSecValueData as String] = data
            addQuery[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
            let addStatus = SecItemAdd(addQuery as CFDictionary, nil)
            guard addStatus == errSecSuccess else {
                throw KeychainStoreError.saveFailed(addStatus)
            }
        } else if status != errSecSuccess {
            throw KeychainStoreError.saveFailed(status)
        }
    }

    public func get(_ key: KeychainKey) throws -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else {
            throw KeychainStoreError.readFailed(status)
        }
        guard let data = result as? Data, let value = String(data: data, encoding: .utf8) else {
            throw KeychainStoreError.notFound
        }
        return value
    }

    public func delete(_ key: KeychainKey) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue,
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainStoreError.deleteFailed(status)
        }
    }

    public func hasConfiguredAPIKeys() -> Bool {
        let keys: [KeychainKey] = [.tmdbAPIKey, .tvdbAPIKey]
        return keys.contains { (try? get($0))?.isEmpty == false }
    }
}
