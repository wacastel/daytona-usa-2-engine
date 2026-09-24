import Foundation
import CryptoKit

/// Credits belong to the current desktop session. Keep the original cabinet
/// settings, records and accounting intact when starting the next session.
enum DaytonaCabinetSave {
    enum Failure: LocalizedError {
        case invalid(String)
        var errorDescription: String? {
            switch self { case .invalid(let detail): return "Cabinet save was left unchanged: \(detail)" }
        }
    }

    static func shouldClearCredits(bundleIdentifier: String?, arguments: [String]) -> Bool {
        let replayOptions = ["--headless", "--self-test", "--diagnostic-run", "--audio-replay"]
        return bundleIdentifier == "local.william.daytonausa2"
            && !replayOptions.contains(where: arguments.contains)
    }

    /// Find the original one-byte primary credit bank by parsing CBlockFile.
    /// The adjacent byte is another bank, not the upper half of this counter.
    static func clearingCredits(in original: Data) throws -> (data: Data, credits: UInt8) {
        let bytes = [UInt8](original)
        let expected = [("Daytona2 NVRAM", 0), ("93C46", 166), ("Backup RAM", 0x20000)]
        var position = 0, payloads: [Int] = []
        func invalid() -> Failure { .invalid("unrecognized NVRAM structure") }
        func word(_ at: Int) -> Int {
            Int(bytes[at]) | Int(bytes[at + 1]) << 8 | Int(bytes[at + 2]) << 16 | Int(bytes[at + 3]) << 24
        }
        for (name, length) in expected {
            guard bytes.count - position >= 12 else { throw invalid() }
            let size = word(position), nameSize = word(position + 4), commentSize = word(position + 8)
            let header = 12 + nameSize + commentSize
            guard nameSize > 0, commentSize > 0, size >= header,
                  size <= bytes.count - position, size - header == length else { throw invalid() }
            let nameStart = position + 12, commentStart = nameStart + nameSize
            let storedName = bytes[nameStart..<(commentStart - 1)]
            let commentEnd = commentStart + commentSize - 1
            guard bytes[commentStart - 1] == 0, !storedName.contains(0),
                  String(bytes: storedName, encoding: .utf8) == name,
                  bytes[commentEnd] == 0, !bytes[commentStart..<commentEnd].contains(0) else { throw invalid() }
            payloads.append(position + header); position += size
        }
        guard position == bytes.count,
              Array(bytes[payloads[1]..<(payloads[1] + 6)]) == [0x33, 0x4d, 0x45, 0x53, 0x41, 0x47] else {
            throw invalid()
        }
        // Revision A's primary credit byte in the pinned loader's word-swizzled
        // Backup RAM payload. Original program reads/writes this byte without a
        // checksum; coin totals, the second bank and lap records are elsewhere.
        let offset = payloads[2] + 0x1e142
        let credits = bytes[offset]
        guard credits != 0 else { return (original, 0) }
        var updated = original
        updated[offset] = 0
        return (updated, credits)
    }

    @discardableResult
    static func prepareInteractiveLaunch(in directory: URL) throws -> UInt8 {
        let fm = FileManager.default, save = directory.appendingPathComponent("daytona2.nv")
        guard fm.fileExists(atPath: save.path) else { return 0 }
        let attributes = try fm.attributesOfItem(atPath: save.path)
        guard attributes[.type] as? FileAttributeType == .typeRegular else {
            throw Failure.invalid("NVRAM is not a regular file")
        }
        let original = try Data(contentsOf: save)
        let result = try clearingCredits(in: original)
        guard result.credits != 0 else { return 0 }

        let backups = directory.appendingPathComponent("Backups", isDirectory: true)
        try fm.createDirectory(at: backups, withIntermediateDirectories: true)
        guard try fm.attributesOfItem(atPath: backups.path)[.type] as? FileAttributeType == .typeDirectory else {
            throw Failure.invalid("backup location is not a directory")
        }
        let digest = SHA256.hash(data: original).map { String(format: "%02x", $0) }.joined()
        let backup = backups.appendingPathComponent("daytona2-before-startup-\(digest).nv")
        if !fm.fileExists(atPath: backup.path) {
            try original.write(to: backup, options: .withoutOverwriting)
            if let permissions = attributes[.posixPermissions] {
                try fm.setAttributes([.posixPermissions: permissions], ofItemAtPath: backup.path)
            }
        }
        guard try fm.attributesOfItem(atPath: backup.path)[.type] as? FileAttributeType == .typeRegular,
              try Data(contentsOf: backup) == original,
              try Data(contentsOf: save) == original else {
            throw Failure.invalid("save or backup changed during startup")
        }
        try result.data.write(to: save, options: .atomic)
        if let permissions = attributes[.posixPermissions] {
            try fm.setAttributes([.posixPermissions: permissions], ofItemAtPath: save.path)
        }
        return result.credits
    }
}
