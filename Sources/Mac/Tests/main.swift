import Foundation
import GameController

struct CheckError: Error, CustomStringConvertible { let description: String }
var checks = [String]()
func check(_ value: @autoclosure () -> Bool, _ description: String) throws {
    guard value() else { throw CheckError(description: description) }; checks.append(description)
}
func rejected(_ input: DaytonaInput, _ description: String) throws {
    do { try input.validate() } catch { checks.append(description); return }
    throw CheckError(description: description)
}
func rejectedReplay(_ json: String, _ description: String) throws {
    do { let r = try JSONDecoder().decode(DaytonaReplay.self, from: Data(json.utf8)); try r.validate() }
    catch { checks.append(description); return }
    throw CheckError(description: description)
}
func near(_ a: Float, _ b: Float) -> Bool { abs(a-b) < 0.0001 }
func tap(_ c: DaytonaControls, _ key: UInt16) { c.key(key, down: true); c.key(key, down: false) }

do {
    for gear in 0...4 {
        let value = DaytonaInput(steering: -1, accelerator: 1, brake: 1, buttons: 63 | DaytonaButton.gear(gear))
        try value.validate()
        try check(value.requestedGear == gear, "Valid direct selector \(gear) with simultaneous original buttons")
    }
    try rejected(DaytonaInput(steering: .nan), "Reject nonfinite steering")
    try rejected(DaytonaInput(accelerator: .infinity), "Reject infinite accelerator")
    try rejected(DaytonaInput(brake: .nan), "Reject nonfinite brake")
    try rejected(DaytonaInput(steering: 1.01), "Reject steering above range")
    try rejected(DaytonaInput(steering: -1.01), "Reject steering below range")
    try rejected(DaytonaInput(accelerator: 1.1), "Reject accelerator above range")
    try rejected(DaytonaInput(brake: -0.1), "Reject negative brake")
    try rejected(DaytonaInput(buttons: 2048), "Reject unknown gameplay bits")
    try rejected(DaytonaInput(buttons: DaytonaButton.gear1 | DaytonaButton.gear4), "Reject ambiguous simultaneous gear selections")
    try rejected(DaytonaInput(buttons: DaytonaButton.neutral | DaytonaButton.gear1), "Reject neutral and gear together")
    let defaultInput = try JSONDecoder().decode(DaytonaInput.self, from: Data("{}".utf8))
    try check(defaultInput == DaytonaInput() && defaultInput.requestedGear == nil, "Missing replay values are neutral and retain the gearbox latch")
    let route = try JSONDecoder().decode(DaytonaReplay.self, from: Data(#"{"steps":[{"frames":2,"accelerator":1,"buttons":128},{"frames":1,"buttons":4}]}"#.utf8))
    try route.validate()
    try check(route.frames == 3 && route.input(frame: 0).accelerator == 1 && route.input(frame: 2).buttons == 4 && route.input(frame: 3) == DaytonaInput(), "Replay exact frame boundaries and neutral end")
    let roundTrip = try JSONDecoder().decode(DaytonaInput.self, from: JSONEncoder().encode(route.input(frame: 0)))
    try check(roundTrip == route.input(frame: 0), "Input JSON preserves analog values, absolute gear")
    let events = try JSONDecoder().decode(DaytonaReplay.self, from: Data(#"{"events":[{"start":2,"end":6,"accelerator":1},{"start":3,"end":4,"buttons":2},{"start":4,"end":5,"accelerator":0.4}]}"#.utf8))
    try events.validate()
    try check(events.frames == 6 && events.input(frame: 1) == DaytonaInput() && events.input(frame: 3).accelerator == 1 && events.input(frame: 3).buttons == 2 && near(events.input(frame: 4).accelerator, 0.4) && events.input(frame: 6) == DaytonaInput(), "Event replay matches laboratory half-open ranges and ordered field merging")
    let tail = try JSONDecoder().decode(DaytonaReplay.self, from: Data(#"{"frames":8,"events":[{"start":0,"end":2,"accelerator":1}]}"#.utf8))
    try tail.validate()
    try check(tail.frames == 8 && tail.input(frame: 1).accelerator == 1 && tail.input(frame: 7) == DaytonaInput(), "Declared event duration preserves neutral replay tail")
    let neutral = try JSONDecoder().decode(DaytonaReplay.self, from: Data(#"{"frames":8,"events":[]}"#.utf8))
    try neutral.validate()
    try check(neutral.frames == 8 && neutral.input(frame: 7) == DaytonaInput(), "Empty events permit explicitly bounded neutral replay")
    for (json, reason) in [
        (#"{"steps":[]}"#, "Reject empty replay"),
        (#"{"steps":[],"events":[]}"#, "Reject ambiguous dual replay formats"),
        (#"{"events":[{"start":2,"end":2}]}"#, "Reject empty event range"),
        (#"{"events":[{"start":-1,"end":2}]}"#, "Reject negative event start"),
        (#"{"events":[]}"#, "Reject empty event replay without frame count"),
        (#"{"frames":1,"events":[{"start":0,"end":2}]}"#, "Reject event beyond declared duration"),
        (#"{"frames":0,"events":[]}"#, "Reject zero declared duration"),
        (#"{"frames":2,"steps":[{"frames":1}]}"#, "Reject inconsistent step duration"),
        (#"{"steps":[{"frames":0}]}"#, "Reject zero-length replay step"),
        (#"{"steps":[{"frames":-1}]}"#, "Reject negative replay step"),
        (#"{"steps":[{"frames":1000000},{"frames":1}]}"#, "Reject replay exceeding frame budget"),
        (#"{"steps":[{"frames":1,"buttons":384}]}"#, "Reject ambiguous gear in replay")
    ] { try rejectedReplay(json, reason) }

    let c = DaytonaControls()
    var pauses = 0, resumes = 0
    c.onTogglePause = { pauses += 1; c.setPaused(!c.paused) }
    c.onResume = { resumes += 1; c.setPaused(false) }
    tap(c, 34)
    try check(c.input() == DaytonaInput(), "Unassigned I does not alter original arcade controls")
    for (key, mask): (UInt16, UInt32) in [(8,1),(36,2),(76,2),(122,4),(120,8),(99,16),(118,32)] {
        tap(c, key)
        try check(c.input().buttons == mask, "Keyboard \(key) maps to bit \(mask), retaining short taps")
        c.consumedFrame(); try check(c.input().buttons == 0, "Keyboard tap \(key) clears after a consumed frame")
    }
    c.key(124, down: true); c.key(13, down: true); c.key(1, down: true)
    try check(c.input().steering == 1 && c.input().accelerator == 1 && c.input().brake == 1, "Keyboard steering and independent pedals")
    c.key(123, down: true); try check(c.input().steering == 0, "Opposite keyboard steering cancels")
    c.clear(); tap(c, 126); tap(c, 125)
    try check(c.input().accelerator == 1 && c.input().brake == 1, "Short Up/Down pedal aliases are retained until a frame")
    c.consumedFrame(); try check(c.input() == DaytonaInput(), "Consumed short pedal taps clear")
    for (key, gear): (UInt16, Int) in [(18,1),(19,2),(20,3),(21,4),(45,0)] {
        tap(c, key)
        try check(c.input().requestedGear == gear && c.selectedGear == gear, "Direct keyboard selector \(gear)")
        c.consumedFrame()
        try check(c.input().requestedGear == nil && c.selectedGear == gear, "Release retains selector \(gear) without resending a command")
    }
    tap(c, 18); tap(c, 21); tap(c, 19)
    try check(c.input().buttons == DaytonaButton.gear2, "Latest direct gear wins across display polls without a frame")
    try c.input().validate(); c.consumedFrame()
    c.key(14, down: true); c.key(14, down: true); c.key(14, down: true, repeated: true)
    try check(c.selectedGear == 3 && c.input().requestedGear == 3, "Held/repeated E shifts only once")
    c.key(14, down: false); c.consumedFrame(); tap(c, 14); tap(c, 14)
    try check(c.selectedGear == 4, "Sequential up requests stop at gear four")
    c.consumedFrame(); tap(c, 12)
    try check(c.input().requestedGear == 3, "Q steps down from committed gear")
    c.consumedFrame(); c.key(12, down: true); c.key(14, down: true)
    try check(c.selectedGear == 3 && c.input().requestedGear == nil, "Opposed Q/E before a frame cancel without an ambiguous selector")
    c.clearKeyboard(); c.consumedFrame(); tap(c, 45); c.consumedFrame(); tap(c, 12)
    try check(c.selectedGear == 0, "Down request stops at neutral")
    c.consumedFrame(); tap(c, 20); c.consumedFrame(); tap(c, 21); c.setActive(false)
    try check(c.selectedGear == 3 && c.input() == DaytonaInput(), "Focus loss discards only unconsumed gear and retains committed latch")
    c.setActive(true); tap(c, 35)
    try check(c.paused && pauses == 1 && c.selectedGear == 3, "P pauses without changing committed gear")
    tap(c, 18); tap(c, 14)
    try check(c.selectedGear == 3 && c.input() == DaytonaInput(), "Paused gear controls do not queue changes")
    tap(c, 36)
    try check(!c.paused && resumes == 1 && c.input().buttons == 0 && c.selectedGear == 3, "Return resumes without delivering Start or changing gear")
    c.resetGearSelector()
    try check(c.selectedGear == 0 && c.input() == DaytonaInput(), "Host reset clears selector to neutral and pending controls")
    c.consumedFrame(DaytonaInput(buttons: DaytonaButton.gear4))
    tap(c, 12); try check(c.input().requestedGear == 3, "Consumed replay gear synchronizes subsequent relative shifting")
    c.consumedFrame()

    let primary = GCController.withExtendedGamepad(), extra = GCController.withExtendedGamepad()
    let pad = primary.extendedGamepad!
    pad.rightTrigger.setValue(1)
    try check(!c.refreshControllers([primary]), "Initial controller assignment is not a disconnect")
    c.pollController(); try check(c.input() == DaytonaInput(), "Held pedal on connect requires neutral")
    pad.rightTrigger.setValue(0); c.pollController()
    pad.leftThumbstick.xAxis.setValue(0.56); pad.rightTrigger.setValue(0.65); pad.leftTrigger.setValue(0.4); c.pollController()
    try check(near(c.input().steering, 0.5) && near(c.input().accelerator, 0.65) && near(c.input().brake, 0.4), "Analog deadzone remap and independent proportional pedals")
    pad.leftThumbstick.xAxis.setValue(0.1); c.pollController(); try check(c.input().steering == 0, "Steering center deadzone")
    pad.leftThumbstick.xAxis.setValue(-1); c.pollController(); try check(c.input().steering == -1, "Full left analog range")
    pad.leftThumbstick.xAxis.setValue(1); c.pollController(); try check(c.input().steering == 1, "Full right analog range")
    pad.dpad.xAxis.setValue(-1); c.pollController(); try check(c.input().steering == -1, "D-pad overrides left stick")
    c.key(124, down: true); try check(c.input().steering == 1, "Keyboard steering overrides controller")
    c.clearKeyboard(); pad.dpad.xAxis.setValue(0); pad.leftThumbstick.xAxis.setValue(0)
    pad.rightTrigger.setValue(0); pad.leftTrigger.setValue(0); c.pollController()
    for (button, mask) in [(pad.buttonB,UInt32(1)),(pad.buttonMenu,2),(pad.buttonA,4),(pad.buttonX,8)] {
        c.consumedFrame(); button.setValue(1); c.pollController(); button.setValue(0); c.pollController()
        try check(c.input().buttons == mask, "Controller bit \(mask) survives a press/release without a frame")
        c.consumedFrame(); try check(c.input().buttons == 0, "Consumed controller bit \(mask) clears")
    }
    for (x,y,mask): (Float,Float,UInt32) in [(0,1,4),(1,0,8),(0,-1,16),(-1,0,32)] {
        pad.rightThumbstick.xAxis.setValue(x); pad.rightThumbstick.yAxis.setValue(y); c.pollController()
        try check(c.input().buttons == mask, "Right-stick view selector \(mask)")
        pad.rightThumbstick.xAxis.setValue(0); pad.rightThumbstick.yAxis.setValue(0); c.pollController(); c.consumedFrame()
    }
    c.resetGearSelector(); c.pollController()
    pad.rightShoulder.setValue(1); c.pollController(); c.pollController()
    try check(c.selectedGear == 1 && c.input().requestedGear == 1, "Held R1 requests gear one only once")
    pad.rightShoulder.setValue(0); c.pollController(); pad.rightShoulder.setValue(1); c.pollController()
    try check(c.selectedGear == 2 && c.input().buttons == DaytonaButton.gear2, "Second R1 tap replaces the unconsumed absolute selector")
    pad.rightShoulder.setValue(0); c.pollController(); c.consumedFrame()
    try check(c.input().requestedGear == nil && c.selectedGear == 2, "Controller release retains committed gear")
    pad.leftShoulder.setValue(1); pad.rightShoulder.setValue(1); c.pollController()
    try check(c.selectedGear == 2 && c.input().requestedGear == nil, "Simultaneous L1/R1 cancel")
    pad.leftShoulder.setValue(0); pad.rightShoulder.setValue(0); c.pollController()
    pad.leftShoulder.setValue(1); c.pollController(); pad.rightShoulder.setValue(1); c.pollController()
    try check(c.selectedGear == 2 && c.input().requestedGear == nil, "Opposed shoulders across zero-frame polls cancel pending shift")
    pad.leftShoulder.setValue(0); pad.rightShoulder.setValue(0); c.pollController()
    pad.leftShoulder.setValue(1); c.pollController(); pad.leftShoulder.setValue(0); c.pollController()
    try check(c.input().requestedGear == 1, "Short L1 request steps down")
    c.consumedFrame()
    tap(c, 21); pad.leftShoulder.setValue(1); c.pollController()
    try check(c.input().requestedGear == 3, "Controller relative request follows latest keyboard selection")
    tap(c, 18); try check(c.input().buttons == DaytonaButton.gear1, "Later keyboard selector replaces controller pending gear")
    pad.leftShoulder.setValue(0); c.pollController(); c.consumedFrame()
    pad.buttonY.setValue(1); c.pollController(); c.pollController()
    try check(c.input().buttons == 0, "Unassigned Triangle does not alter original arcade controls")
    pad.buttonY.setValue(0); c.pollController(); pad.buttonY.setValue(1); c.pollController()
    pad.buttonY.setValue(0); c.pollController(); pad.leftThumbstick.xAxis.setValue(1); c.pollController()
    try check(!c.refreshControllers([extra,primary]) && c.activeController === primary, "Extra controller preserves primary assignment")
    c.pollController(); try check(c.input().steering == 1, "Ignored controller connect does not gate active steering")
    try check(!c.refreshControllers([primary]), "Ignored controller disconnect is harmless")
    c.pollController(); try check(c.input().steering == 1, "Ignored disconnect retains steering")
    let replacement = extra.extendedGamepad!
    replacement.buttonY.setValue(1); replacement.rightShoulder.setValue(1)
    try check(c.refreshControllers([extra]), "Assigned disconnect is reported")
    c.pollController()
    try check(c.input() == DaytonaInput(), "Replacement held shoulder requires neutral")
    replacement.buttonY.setValue(0); c.pollController(); replacement.buttonY.setValue(1); c.pollController()
    try check(c.input() == DaytonaInput(), "Unassigned Triangle does not release the held-shoulder neutral gate")
    replacement.buttonY.setValue(0); replacement.rightShoulder.setValue(0); c.pollController()
    replacement.buttonY.setValue(0); c.pollController()
    replacement.buttonA.setValue(1); c.pollController(); replacement.buttonA.setValue(0)
    c.setActive(false); c.setActive(true); c.pollController()
    try check(c.input().buttons == 0, "Focus transition discards unconsumed controller taps")
    if let pause = replacement.leftThumbstickButton {
        pause.setValue(1); c.pollController(); c.pollController()
        try check(c.paused && pauses == 2, "L3 pauses once when held")
        pause.setValue(0); c.pollController(); replacement.buttonMenu.setValue(1); c.pollController()
        try check(!c.paused && resumes == 2 && c.input().buttons == 0, "Options resumes without arcade Start")
        replacement.buttonMenu.setValue(0); c.pollController()
    }
    c.onTogglePause = nil; c.onResume = nil
    let reserved = DaytonaControls()
    tap(reserved, 8); tap(reserved, 18)
    let inFlight = reserved.reserveFrame()
    try check(inFlight.buttons == DaytonaButton.coin | DaytonaButton.gear1, "Frame reservation includes the pending tap and selector")
    try check(reserved.input() == DaytonaInput() && reserved.selectedGear == 1, "Reservation consumes only pending input at its frame boundary")
    tap(reserved, 8); tap(reserved, 14)
    try check(inFlight.buttons == DaytonaButton.coin | DaytonaButton.gear1, "In-flight input is immutable when later events arrive")
    let next = reserved.reserveFrame()
    try check(next.buttons == DaytonaButton.coin | DaytonaButton.gear2, "Later repeated coin and relative gear request survive the preceding in-flight frame")
    try check(reserved.reserveFrame() == DaytonaInput(), "Reserved one-shot inputs do not repeat without another event")
    reserved.key(13, down: true)
    try check(reserved.reserveFrame().accelerator == 1 && reserved.reserveFrame().accelerator == 1, "Held pedal continues across independent worker reservations")
    reserved.key(13, down: false); tap(reserved, 21); reserved.setPaused(true)
    try check(reserved.input() == DaytonaInput() && reserved.selectedGear == 2, "Pause clears unreserved future input and retains the in-flight gear")
    reserved.setPaused(false); tap(reserved, 12)
    try check(reserved.reserveFrame().requestedGear == 1, "Resume relative shift follows the last reserved gear")
    _ = reserved.reserveFrame(DaytonaInput(buttons: DaytonaButton.gear4)); tap(reserved, 12)
    try check(reserved.reserveFrame().requestedGear == 3, "Replay reservation updates the gear used by later live shifting")
    tap(reserved, 8); reserved.resetGearSelector()
    try check(reserved.reserveFrame() == DaytonaInput() && reserved.selectedGear == 0, "Reset clears future reservations and the gear selector")
    let result: [String:Any] = ["passed":true,"checks":checks,"checkCount":checks.count,
        "engineLinked":false,"engineStubUsed":false,"physicalControllerActuationTested":false,
        "scope":"Actual input router plus synthetic Apple GameController values. No game, ROM, engine stub, GUI presentation or audio engine is executed."]
    print(String(decoding:try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]),as:UTF8.self))
} catch { fputs("Host input test failed: \(error)\n", stderr); exit(1) }
