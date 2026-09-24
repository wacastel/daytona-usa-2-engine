import Foundation
import GameController

// Gear selectors are explicit requests; the native bridge retains the committed gear.
// The host emits absolute selector requests; it never changes game memory.
final class DaytonaControls {
    var onTogglePause: (() -> Void)?
    var onResume: (() -> Void)?
    private(set) var activeController: GCController?
    private(set) var isActive = true
    private(set) var paused = false
    private var needsNeutral = true
    private var pressed = Set<UInt16>(), pendingKeys = Set<UInt16>()
    private var pendingButtons: UInt32 = 0
    private var lastPause = false, lastUp = false, lastDown = false
    private var lastController = DaytonaInput()
    private var committedGear = 0
    private var pendingGear: Int?
    private var gearSerial: UInt64 = 0
    private struct ShiftUndo { let previous: Int?; let serial: UInt64 }
    private var keyboardShiftUndo: ShiftUndo?, controllerShiftUndo: ShiftUndo?
    var selectedGear: Int { pendingGear ?? committedGear }
    private let gameKeys: Set<UInt16> = [8,36,76,122,120,99,118,13,1,123,124,125,126]
    private let gearKeys: [UInt16:Int] = [45:0,18:1,19:2,20:3,21:4]

    func refreshControllers(_ available: [GCController]) -> Bool {
        let usable = available.filter { $0.extendedGamepad != nil }
        if let current = activeController, usable.contains(where: { $0 === current }) { return false }
        let lostActive = activeController != nil
        activeController = usable.first(where: { $0.extendedGamepad is GCDualSenseGamepad }) ?? usable.first
        activeController?.playerIndex = .index1
        activeController?.extendedGamepad?.buttonMenu.preferredSystemGestureState = .disabled
        activeController?.extendedGamepad?.buttonOptions?.preferredSystemGestureState = .disabled
        clear()
        return lostActive
    }
    func clear() {
        pressed.removeAll(); pendingKeys.removeAll(); pendingButtons = 0; pendingGear = nil
        keyboardShiftUndo = nil; controllerShiftUndo = nil
        needsNeutral = true; lastPause = false; lastUp = false; lastDown = false
        lastController = DaytonaInput()
    }
    func clearKeyboard() { pressed.removeAll(); pendingKeys.removeAll(); keyboardShiftUndo = nil }
    func resetGearSelector() { clear(); committedGear = 0 }
    func setActive(_ value: Bool) { isActive = value; clear() }
    func setPaused(_ value: Bool) { paused = value; clear() }
    private func requestGear(_ gear: Int) {
        pendingGear = min(4, max(0, gear)); gearSerial &+= 1
    }
    private func shift(_ delta: Int) -> ShiftUndo {
        let previous = pendingGear
        requestGear(selectedGear + delta)
        return ShiftUndo(previous: previous, serial: gearSerial)
    }
    private func cancelUnconsumedShift(_ undo: ShiftUndo?) {
        if let undo, undo.serial == gearSerial { pendingGear = undo.previous; gearSerial &+= 1 }
    }
    func key(_ code: UInt16, down: Bool, repeated: Bool = false) {
        guard isActive, !repeated else { return }
        if !down {
            pressed.remove(code)
            if code == 12 || code == 14 { keyboardShiftUndo = nil }
            return
        }
        let fresh = pressed.insert(code).inserted
        if code == 35 || code == 53 { if fresh { onTogglePause?() }; return }
        if paused {
            if fresh && (code == 36 || code == 76) { onResume?() }
            return
        }
        if let gear = gearKeys[code] { if fresh { requestGear(gear) }; return }
        if code == 12 || code == 14 {
            guard fresh else { return }
            let opposite: UInt16 = code == 12 ? 14 : 12
            if pressed.contains(opposite) { cancelUnconsumedShift(keyboardShiftUndo); keyboardShiftUndo = nil }
            else { keyboardShiftUndo = shift(code == 14 ? 1 : -1) }
            return
        }
        if gameKeys.contains(code) { pendingKeys.insert(code) }
    }
    private func steering(_ value: Float) -> Float {
        let deadzone: Float = 0.12
        guard abs(value) > deadzone else { return 0 }
        return min(1, (abs(value) - deadzone) / (1 - deadzone)) * (value < 0 ? -1 : 1)
    }
    func pollController() {
        guard isActive, let pad = activeController?.extendedGamepad else { lastController = DaytonaInput(); return }
        var input = DaytonaInput(steering: steering(pad.leftThumbstick.xAxis.value),
                                 accelerator: max(0, min(1, pad.rightTrigger.value)), brake: max(0, min(1, pad.leftTrigger.value)))
        if abs(pad.dpad.xAxis.value) > 0.25 { input.steering = pad.dpad.xAxis.value < 0 ? -1 : 1 }
        if pad.buttonB.isPressed { input.buttons |= DaytonaButton.coin }
        if pad.buttonMenu.isPressed { input.buttons |= DaytonaButton.start }
        if pad.buttonA.isPressed { input.buttons |= DaytonaButton.view1 }
        if pad.buttonX.isPressed { input.buttons |= DaytonaButton.view2 }
        let rx = pad.rightThumbstick.xAxis.value, ry = pad.rightThumbstick.yAxis.value
        if max(abs(rx), abs(ry)) > 0.6 {
            if abs(ry) >= abs(rx) { input.buttons |= ry > 0 ? DaytonaButton.view1 : DaytonaButton.view3 }
            else { input.buttons |= rx > 0 ? DaytonaButton.view2 : DaytonaButton.view4 }
        }
        let pause = pad.leftThumbstickButton?.isPressed == true
        let up = pad.rightShoulder.isPressed, down = pad.leftShoulder.isPressed
        if needsNeutral {
            if input.buttons == 0 && input.steering == 0 && input.accelerator < 0.03 && input.brake < 0.03 && !pause && !up && !down {
                needsNeutral = false
            }
            lastPause = pause; lastUp = up; lastDown = down
            lastController = DaytonaInput(); return
        }
        if pause && !lastPause { onTogglePause?(); lastPause = pause; lastController = DaytonaInput(); return }
        lastPause = pause
        if paused && input.buttons & DaytonaButton.start != 0 { onResume?(); lastController = DaytonaInput(); return }
        if !paused {
            if up && down { cancelUnconsumedShift(controllerShiftUndo); controllerShiftUndo = nil }
            else if up && !lastUp { controllerShiftUndo = shift(1) }
            else if down && !lastDown { controllerShiftUndo = shift(-1) }
            else if !up && !down { controllerShiftUndo = nil }
            pendingButtons |= input.buttons
        }
        lastUp = up; lastDown = down
        lastController = input
    }
    func input() -> DaytonaInput {
        guard isActive, !paused else { return DaytonaInput() }
        let keys = pressed.union(pendingKeys)
        var result = lastController
        result.buttons |= pendingButtons
        for (code, bit): (UInt16, UInt32) in [(8,DaytonaButton.coin),(36,DaytonaButton.start),(76,DaytonaButton.start),
          (122,DaytonaButton.view1),(120,DaytonaButton.view2),(99,DaytonaButton.view3),(118,DaytonaButton.view4)] {
            if keys.contains(code) { result.buttons |= bit }
        }
        if let gear = pendingGear { result.buttons |= DaytonaButton.gear(gear) }
        if !keys.isDisjoint(with: [123,124]) { result.steering = (keys.contains(124) ? 1 : 0) - (keys.contains(123) ? 1 : 0) }
        if !keys.isDisjoint(with: [13,126]) { result.accelerator = 1 }
        if !keys.isDisjoint(with: [1,125]) { result.brake = 1 }
        return result
    }
    // A threaded producer reserves exactly one imminent engine frame while its
    // caller holds the routing lock. It must not acknowledge the frame again
    // on completion: later taps belong to the next frame.
    func reserveFrame(_ replayInput: DaytonaInput? = nil) -> DaytonaInput {
        let value = replayInput ?? input()
        consumedFrame(value)
        return value
    }
    // Commit input at an engine frame boundary, including replay input.
    func consumedFrame(_ consumed: DaytonaInput? = nil) {
        if let consumed {
            if let gear = consumed.requestedGear { committedGear = gear }
        } else if let gear = pendingGear { committedGear = gear }
        pendingKeys.removeAll(); pendingButtons = 0; pendingGear = nil
        keyboardShiftUndo = nil; controllerShiftUndo = nil
    }
}
