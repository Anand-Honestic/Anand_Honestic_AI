//
//  AthenaIOSBridge.swift
//  ATHENA Phone AI — iOS Secondary Companion Client
//
//  Non-Negotiable Architecture Constraints:
//  1. No AccessibilityService on iOS (Sandboxed execution only).
//  2. App automation executed via Siri Shortcuts & Universal / Custom URL Schemes.
//  3. Background wakeup driven by silent APNs push with 30-second execution window.
//  4. Secrets stored in Secure Enclave Apple Keychain.
//

import Foundation
import LocalAuthentication
import Security

public enum AthenaIOSError: Error {
    case biometricsFailed
    case invalidURLScheme
    case appNotInstalled
    case unauthenticated
}

public class AthenaIOSBridge {
    
    public static let shared = AthenaIOSBridge()
    private init() {}
    
    /// Verifies Face ID / Touch ID before executing sensitive Tier 3 actions on iOS
    public func authenticateBiometrics(reason: String, completion: @escaping (Result<Bool, AthenaIOSError>) -> Void) {
        let context = LAContext()
        var error: NSError?
        
        if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
            context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: reason) { success, _ in
                DispatchQueue.main.async {
                    if success {
                        completion(.success(true))
                    } else {
                        completion(.failure(.biometricsFailed))
                    }
                }
            }
        } else {
            // Biometrics unavailable
            completion(.failure(.biometricsFailed))
        }
    }
    
    /// Dispatches an action via Siri Shortcuts or URL Schemes
    public func executeAction(schemeUrlString: String, completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: schemeUrlString) else {
            completion(false)
            return
        }
        
        DispatchQueue.main.async {
            // Simulates openURL on UIApplication
            print("[AthenaIOSBridge] 🔗 Dispatched iOS URL Scheme: \(url.absoluteString)")
            completion(true)
        }
    }
    
    /// Securely persists device identity key into Apple Keychain
    public func saveKeychainSecret(key: String, data: Data) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        SecItemDelete(query as CFDictionary)
        let status = SecItemAdd(query as CFDictionary, nil)
        return status == errSecSuccess
    }
    
    /// Retrieves secret from Apple Keychain
    public func loadKeychainSecret(key: String) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var dataTypeRef: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)
        if status == errSecSuccess {
            return dataTypeRef as? Data
        }
        return nil
    }
}

