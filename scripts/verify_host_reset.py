#!/usr/bin/env python3
"""Exercise the real Swift cold-reset path after racing and compare a fresh boot."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from import_assets import ROOT, sha, write_json

HARNESS = r'''
import Foundation
import CryptoKit

func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() { throw DaytonaUSA2Error.message(message) }
}
func run() throws {
    let args = CommandLine.arguments
    let mode = args[1], output = URL(fileURLWithPath: args[2], isDirectory: true)
    let route = try JSONDecoder().decode(DaytonaReplay.self, from: Data(contentsOf: URL(fileURLWithPath: args[3])))
    let frames = Int(args[4])!
    try route.validate()
    let game = try DaytonaGame(); defer { game.close() }
    try require(!Thread.isMainThread, "Engine harness must stay on its dedicated thread")
    var before: [String: Any] = [:], reset: [String: Any] = [:]
    if mode == "reset" {
        for frame in 0..<frames {
            _ = try autoreleasepool { try game.advance(route.input(frame: frame)) }
        }
        try game.setTimerFrozen(true)
        for frame in frames..<(frames + 60) {
            _ = try autoreleasepool { try game.advance(route.input(frame: frame)) }
        }
        before = game.diagnostics()
        try require(before["timerFrozen"] as? Bool == true, "Timer did not enable before reset")
        try game.reset()
        reset = game.diagnostics()
        try require(game.frameCount == 0 && game.sampleFrames == 0 && game.latestFrame == nil,
                    "Reset retained an old frame or audio count")
        try require(reset["timerFrozen"] as? Bool == false && reset["closed"] as? Bool == false,
                    "Reset did not open a fresh unfrozen context")
        // Copy only the disposable saved cabinet settings that the new context
        // loaded. The independent baseline gets the same NVRAM, not a RAM state.
        let saves = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DAYTONA_USA_2_SAVE_DIR"]!)
        try FileManager.default.copyItem(at: saves.appendingPathComponent("daytona2.nv"),
                                         to: output.appendingPathComponent("baseline.nv"))
    }
    let trace = output.appendingPathComponent(mode + "-trace.jsonl")
    try Data().write(to: trace)
    let file = try FileHandle(forWritingTo: trace); defer { try? file.close() }
    var pictures = SHA256(), audio = SHA256()
    func digest(_ value: SHA256.Digest) -> String { value.map { String(format: "%02x", $0) }.joined() }
    for frame in 0..<frames {
        try autoreleasepool {
            let samples = try game.advance(route.input(frame: frame))
            let rgba = game.latestFrame!.rgba, pcm = samples.withUnsafeBytes { Data($0) }
            pictures.update(data: rgba); audio.update(data: pcm)
            let row: [String: Any] = ["frame": frame + 1, "audioFrames": samples.count / 2,
                "rgba": digest(SHA256.hash(data: rgba)), "pcm": digest(SHA256.hash(data: pcm))]
            var data = try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
            data.append(10); try file.write(contentsOf: data)
        }
    }
    let report: [String: Any] = ["passed": true, "frames": frames, "mode": mode,
        "beforeReset": before, "afterReset": reset, "finalState": game.diagnostics(),
        "sampleFrames": game.sampleFrames, "pictureSHA256": digest(pictures.finalize()),
        "audioSHA256": digest(audio.finalize()), "engineCallsOnDedicatedThread": !Thread.isMainThread]
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
        .write(to: output.appendingPathComponent(mode + ".json"))
    try game.latestFrame!.writePNG(to: output.appendingPathComponent(mode + ".png"))
}
Thread.detachNewThread {
    autoreleasepool {
        do { try run(); exit(0) }
        catch { fputs("Host reset verification failed: \(error)\n", stderr); exit(1) }
    }
}
dispatchMain()
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--frames', type=int, default=3000)
    ap.add_argument('--output', type=Path, default=ROOT/'build/controls-update/reset')
    args = ap.parse_args()
    if not 2400 <= args.frames <= 4272:
        raise ValueError('Use 2400–4272 frames to exercise racing within the accepted route')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = ROOT/'build/native/libdaytona2.a'
    manifest = ROOT/'build/native/engine-build-manifest.json'
    engine = json.loads(manifest.read_text())
    if not engine['shippingNative'] or engine['diagnostics'] or engine['staticArchiveSHA256'] != sha(archive):
        raise RuntimeError('A current shipping native archive is required')
    sources = [ROOT/name for name in ['Sources/Mac/Input.swift', 'Sources/Mac/Media.swift', 'Sources/Mac/CabinetSave.swift', 'Sources/Mac/NativeGame.swift']]
    route = ROOT/'Configuration/replays/beginner-auto.json'
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in [*sources, archive, manifest, route, Path(__file__).resolve()]}
    harness = output/'main.swift'
    harness.write_text(HARNESS)
    executable = output/'host-reset'
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
    command = ['xcrun', 'swiftc', '-swift-version', '5', '-target', 'arm64-apple-macosx14.0', '-sdk', sdk, '-O']
    for framework in ['AppKit', 'SpriteKit', 'AVFoundation', 'GameController', 'CoreGraphics', 'IOKit', 'CoreFoundation', 'OpenGL', 'CoreVideo']:
        command += ['-framework', framework]
    command += [str(p) for p in sources] + [str(harness), str(archive), '-lc++', '-lz', '-o', str(executable)]
    subprocess.run(command, cwd=ROOT, check=True)
    baseline_nv = output/'baseline.nv'
    baseline_nv.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='reset-saves-', dir=output) as saves, tempfile.TemporaryDirectory(prefix='fresh-saves-', dir=output) as fresh:
        environment = {**os.environ, 'DAYTONA2_RTC_EPOCH': '946684800', 'DAYTONA_USA_2_ASSET_DIR': str(ROOT/'build/assets')}
        for mode, directory in [('reset', saves), ('fresh', fresh)]:
            if mode == 'fresh':
                shutil.copy2(baseline_nv, Path(fresh)/'daytona2.nv')
            environment['DAYTONA_USA_2_SAVE_DIR'] = directory
            with (output/(mode+'.log')).open('w') as log:
                subprocess.run([str(executable), mode, str(output), str(route), str(args.frames)],
                               env=environment, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    reset = json.loads((output/'reset.json').read_text())
    fresh = json.loads((output/'fresh.json').read_text())
    reset_trace = (output/'reset-trace.jsonl').read_bytes()
    fresh_trace = (output/'fresh-trace.jsonl').read_bytes()
    if reset_trace != fresh_trace:
        left = [json.loads(x) for x in reset_trace.splitlines()]
        right = [json.loads(x) for x in fresh_trace.splitlines()]
        differing = [i+1 for i, (a,b) in enumerate(zip(left,right)) if a != b]
        raise AssertionError(f'Cold restart/fresh boot differ at {len(differing)} frames, first {differing[:10]}')
    if any(sha(ROOT/name) != value for name,value in inputs.items()):
        raise RuntimeError('Host reset verification inputs changed during the run')
    result = {'passed': True, 'inputs': inputs, 'harnessSHA256': sha(harness), 'executableSHA256': sha(executable),
              'framesBeforeReset': args.frames+60, 'framesAfterReset': args.frames,
              'framesInIndependentFreshBoot': args.frames, 'sameSaveDirectoryAcrossReset': True,
              'baselineUsesCopiedCabinetNVRAMOnly': True, 'timerFrozenBeforeReset': True,
              'timerOffAndFrameZeroAfterReset': True, 'exactPostResetRGBA_PCM_CountAgreement': True,
              'postResetTraceSHA256': sha(output/'reset-trace.jsonl'), 'reset': reset, 'fresh': fresh,
              'scope': 'Actual Swift DaytonaGame reset on a dedicated thread saves cabinet settings, destroys and recreates the native context after racing with timer assistance, then matches every picture, PCM block and sample count from an independent fresh process loaded with the same saved NVRAM. No GUI, physical controller or complete-game claim.'}
    write_json(output/'acceptance.json', result)
    write_json(ROOT/'Documentation/host-reset-acceptance.json', result)
    print(json.dumps({'passed': True, 'framesBeforeReset': args.frames+60, 'framesCompared': args.frames,
                      'report': str(output/'acceptance.json')}))


if __name__ == '__main__':
    main()
