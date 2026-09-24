import Foundation

enum DaytonaUSA2Error: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let value) = self { return value }; return nil }
}
enum DaytonaButton {
    static let coin: UInt32 = 1, start: UInt32 = 2
    static let view1: UInt32 = 4, view2: UInt32 = 8, view3: UInt32 = 16, view4: UInt32 = 32
    static let neutral: UInt32 = 64, gear1: UInt32 = 128, gear2: UInt32 = 256
    static let gear3: UInt32 = 512, gear4: UInt32 = 1024, all: UInt32 = 2047
    static let gearMask: UInt32 = neutral | gear1 | gear2 | gear3 | gear4
    static func gear(_ value: Int) -> UInt32 { UInt32(64) << value }
}
struct DaytonaInput: Codable, Equatable {
    var steering: Float = 0, accelerator: Float = 0, brake: Float = 0
    var buttons: UInt32 = 0
    init(steering: Float = 0, accelerator: Float = 0, brake: Float = 0, buttons: UInt32 = 0) {
        self.steering = steering; self.accelerator = accelerator; self.brake = brake
        self.buttons = buttons
    }
    private enum CodingKeys: String, CodingKey { case steering, accelerator, brake, buttons }
    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        steering = try values.decodeIfPresent(Float.self, forKey: .steering) ?? 0
        accelerator = try values.decodeIfPresent(Float.self, forKey: .accelerator) ?? 0
        brake = try values.decodeIfPresent(Float.self, forKey: .brake) ?? 0
        buttons = try values.decodeIfPresent(UInt32.self, forKey: .buttons) ?? 0
    }
    func validate() throws {
        guard steering.isFinite, accelerator.isFinite, brake.isFinite,
              (-1...1).contains(steering), (0...1).contains(accelerator), (0...1).contains(brake), buttons & ~DaytonaButton.all == 0, (buttons & DaytonaButton.gearMask).nonzeroBitCount <= 1 else {
            throw DaytonaUSA2Error.message("Invalid driving input: steering must be -1…1, pedals 0…1, and defined button flags with at most one gear selector.")
        }
    }
    var requestedGear: Int? {
        let bits = buttons & DaytonaButton.gearMask
        guard bits.nonzeroBitCount == 1 else { return nil }
        return bits.trailingZeroBitCount - 6
    }
    var diagnostic: [String: Any] {
        let value: [String: Any] = ["steering": steering, "accelerator": accelerator, "brake": brake, "buttons": buttons]
        return value
    }
}
struct DaytonaReplay: Decodable {
    struct Step: Decodable {
        let frames: Int
        let input: DaytonaInput
        private enum CodingKeys: String, CodingKey { case frames }
        init(from decoder: Decoder) throws {
            frames = try decoder.container(keyedBy: CodingKeys.self).decode(Int.self, forKey: .frames)
            input = try DaytonaInput(from: decoder)
        }
    }
    struct Event: Decodable {
        let start: Int, end: Int
        let steering: Float?, accelerator: Float?, brake: Float?
        let buttons: UInt32?
        func applying(to input: DaytonaInput) -> DaytonaInput {
            DaytonaInput(steering: steering ?? input.steering,
                         accelerator: accelerator ?? input.accelerator,
                         brake: brake ?? input.brake, buttons: buttons ?? input.buttons)
        }
    }
    let steps: [Step]
    let events: [Event]?
    let declaredFrames: Int?
    private enum CodingKeys: String, CodingKey { case steps, events, frames }
    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        guard values.contains(.steps) != values.contains(.events) else {
            throw DaytonaUSA2Error.message("A replay must contain either steps or events.")
        }
        steps = try values.decodeIfPresent([Step].self, forKey: .steps) ?? []
        events = try values.decodeIfPresent([Event].self, forKey: .events)
        declaredFrames = try values.decodeIfPresent(Int.self, forKey: .frames)
    }
    var frames: Int { declaredFrames ?? events?.map(\.end).max() ?? steps.reduce(0) { $0 + $1.frames } }
    func validate() throws {
        if let declaredFrames, !(1...1_000_000).contains(declaredFrames) {
            throw DaytonaUSA2Error.message("A replay is limited to one million frames and must contain at least one frame.")
        }
        if let events {
            guard frames > 0 else { throw DaytonaUSA2Error.message("An empty event replay must declare its frame count.") }
            for event in events {
                guard event.start >= 0, event.end > event.start, event.end <= min(frames, 1_000_000) else {
                    throw DaytonaUSA2Error.message("Replay events require 0 ≤ start < end within the replay frame count.")
                }
                try event.applying(to: DaytonaInput()).validate()
            }
            return
        }
        guard !steps.isEmpty else { throw DaytonaUSA2Error.message("A replay must contain at least one step.") }
        var total = 0
        for step in steps {
            try step.input.validate()
            guard (1...1_000_000).contains(step.frames), total <= 1_000_000 - step.frames else {
                throw DaytonaUSA2Error.message("A replay is limited to one million frames.")
            }
            total += step.frames
        }
        if let declaredFrames, declaredFrames != total {
            throw DaytonaUSA2Error.message("A step replay's declared frame count must equal the sum of its steps.")
        }
    }
    func input(frame: Int) -> DaytonaInput {
        if let events {
            // Match the laboratory replay: active events merge fields in file order.
            return events.filter { $0.start <= frame && frame < $0.end }
                .reduce(DaytonaInput()) { $1.applying(to: $0) }
        }
        var end = 0
        for step in steps { end += step.frames; if frame < end { return step.input } }
        return DaytonaInput()
    }
}
