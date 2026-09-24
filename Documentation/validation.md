# Validation evidence

This report records the bounded qualification of Daytona USA 2: Battle on the
Edge, Revision A (`daytona2`) on arm64 macOS. Processor fixtures and all four
final reference/native gameplay comparisons have passed, as have packaged-host
replay, the final live window/audio telemetry check, and independent
clean-source generation, integration and packaged-host checks. The evidence and
its precise coverage are recorded below.

The input is the 47-file media set identified in
[media acceptance](media-acceptance.json). Import checks file lengths, CRC32,
SHA-1 and SHA-256. Fresh saves use USA / SINGLE settings produced by replaying
the original service menus, then checked against the original EEPROM identity.
No ROM or save bytes are patched to establish those settings. Existing user
saves are separate from qualification saves. The
[cabinet settings record](cabinet-settings.md) describes the 2,485-frame setup
route and the checked fields.

The reference retains the original processor implementations from Supermodel
commit `24d2ffcfc7f14229337f05f4920fe26b56633d9d`. The native engine substitutes
fixed programs generated offline from the verified ROMs and captured executable
uploads. Runtime execution selects a compiled entry by original address and
checks its expected instruction identity; unknown or changed instructions fail
explicitly. The product has no runtime CPU/DSP opcode decoder, runtime compiler,
or interpreter fallback. Source and generated-program identities are bound by
the engine build manifest.

The reference and native builds share the retained board, rendering and audio
devices, the same single-cabinet configuration, and the documented macOS bridge
adaptations. The reference is therefore an original-processor comparison build,
not an untouched upstream application or an independent hardware model. See
[architecture](architecture.md) for these boundaries.

| Processor or program | Differential evidence | Result |
| --- | --- | --- |
| PowerPC 603R | 1,892 ROM samples across 157 handler families and all 203 admitted helper starts, each in eight register states: 16,760 comparisons | Exact state and bus-write agreement; unknown address and changed instruction rejected |
| Both sound-board 68000 contexts | 15,526 instruction trials, including registers, flags, PC, cycles, ordered bus reads/writes and stop state | Exact agreement; changed opcode, changed extension word and unknown PC rejected |
| Two SCSP DSPs | 253 complete or transient fixed images; 4,048 state/sample-RAM trials, 1,256 execution-limit trials and 48 synthetic trials | Exact agreement; unknown executing program rejected |
| Wheel-board Z80 | Every one of 36,864 mapped ROM byte starts in four register/interrupt states: 147,456 comparisons | Exact agreement through the immediate interrupt boundary; unknown address and changed bytes rejected |

The detailed [PowerPC](ppc-acceptance.json), [sound](sound-acceptance.json) and
[Z80](z80-acceptance.json) reports bind compiler flags, generators, fixtures,
original sources and generated outputs. These are sampled-state comparisons,
not an enumeration of every possible machine state. The PowerPC generator
specializes 71,344 fixed operations; its fixture does not test every such
operation in every state. The Z80 keeps the pinned implementation's interrupt
and HALT limitations.

The [sound lifecycle check](sound-lifecycle-acceptance.json) also compares two
fresh game contexts, each running 2,400 Beginner automatic frames, in one process
across destruction and recreation. Every picture, PCM block and sample count
matches between sessions and against a preserved first-process baseline, with
zero differing frames. The shared derived SCSP initialization clears the
inherited sound-CPU cycle remainder at cold initialization. This preserves
original first-process scheduling; the accepted fixture uses the public C ABI
and does not patch private globals or restart the process between sessions.

The PowerPC helper at `0x0063d000` was independently captured during Advanced,
Expert and manual gameplay. All three executable images match exactly over
2,396 bytes, ending immediately after the return at `0x0063d958`. All executed
PowerPC identities in 15 observation traces match either the verified static
program/RAM alias or that helper image. A separate 4 KiB diagnostic page is
retained locally; data following the executable boundary is excluded from the
admitted helper code. Generation also rejects observations that conflict with
the supplied immutable image. These captures establish the exercised upload
identity, not exhaustive future reachability.

Gameplay comparison runs the actual reference and native engines in independent
processes with fresh isolated saves, identical ordered input events, and a fixed
RTC epoch of `946684800`. At every frame it compares SHA-256 identities of the
496×384 RGBA picture and interleaved signed 16-bit stereo PCM block, plus the
exact stereo-frame count. It requires nonzero PCM data and verifies that engine,
route, media and validation-source identities did not change during the run.
The bridge supplies 735 stereo frames per step at its declared 60 steps/second
and 44,100 Hz. This retains the selected source's scheduling conventions; it is
not a physical-board timing measurement.

| Authored route | Frames | Exercised gameplay | Final native/reference comparison |
| --- | ---: | --- | --- |
| [Beginner automatic](../Configuration/replays/beginner-auto.json) | 4,332 | Original selection menus and automatic racing | Passed: all pictures, PCM blocks and sample counts match |
| [Beginner manual](../Configuration/replays/beginner-manual.json) | 9,500 | Manual selection and gear inputs, time expiry, subsequent course/car menus and another engine-start sequence | Passed: all pictures, PCM blocks and sample counts match |
| [Advanced automatic](../Configuration/replays/advanced-auto.json) | 4,500 | LAP 1/4 racing, all camera views, steering, pedals, collisions and a time-extension checkpoint | Passed: all pictures, PCM blocks and sample counts match |
| [Expert automatic](../Configuration/replays/expert-auto.json) | 4,500 | LAP 1/2 racing, all camera views, steering, pedals, collisions and reverse warning | Passed: all pictures, PCM blocks and sample counts match |

The suite covers all three courses and both transmission modes. Manual
transmission is exercised on Beginner; it is not a six-way course/transmission
matrix. Advanced and Expert each include more than 2,000 verified live racing
frames. These routes do not demonstrate completed races, all laps, wins,
every car, every menu choice or every possible gameplay state. The manual
route's tail shows time expiry and subsequent menus; it is not evidence of a
completed race or an attract-mode transition.

The final [integration report](integration-acceptance.json) records **22,832 exact
frame comparisons and 16,781,520 stereo sample frames**, with nonzero PCM on
every route. It binds the accepted native library
`944067c3c20a86fd0b88a690b6799d1ec6d108de882186cd27d3021a263acb13`,
the reference library, archive, media, routes and validation sources. These
comparisons were rerun after the sound lifecycle change. Concurrent replay
processes share the GPU, so their elapsed times are not live-application
performance measurements.

The [bridge checks](bridge-acceptance.json) passed 35 real native-engine cases:
media identity, lifecycle, invalid numeric inputs, conflicting gears, unexposed
or unknown input bits, no advancement after rejected input, recovery, reset,
save and recreation. The [package audit](package-acceptance.json) also passed: arm64 executable
and native library, macOS 14 deployment target, system-only dependencies,
expected fixed-execution symbols, no matched decoder/diagnostic symbols,
resource/source identities and ad hoc signature. Symbol inspection alone does
not prove execution semantics.

The package verifier subsequently gained an explicit check that the native
dylib matches its engine manifest. Repackaging produced the same bytes for all
14 application files, including the executable, media and signature resources.
The [package requalification record](package-requalification.json) binds the
prior and current manifests, their sole verifier-source hash difference, the
complete application inventory, and the retained host/live/UI reports. Those
reports therefore still apply to the identical application bytes; their older
package-manifest references are intentional. The strengthened package audit was
rerun, while gameplay was not redundantly replayed for this audit-only change.

The [packaged-host check](host-acceptance.json) passed all 9,500 frames and
6,982,500 stereo sample frames of the Beginner manual route, comparing every
picture, PCM block and count from the real Swift executable and bundled media
with the accepted direct-engine trace. Two additional fresh sessions in one
process each ran 2,400 frames and produced identical picture/audio identities
and 1,764,000 stereo sample frames per session. The final engine fault code was
zero. These headless checks qualify the package's engine linkage, media and
session lifecycle; they do not exercise the display or output audio device.

The GUI host now owns one persistent engine thread for graphics-context
creation, stepping, reset and destruction. It produces audio independently of
SpriteKit and passes immutable frame snapshots to the main-thread presenter.
The [host input report](host-input-acceptance.json) records 123 passed checks,
including immutable in-flight inputs,
retention of later taps, pause/resume and committed gear behavior. Those checks
use synthetic Apple controller values and do not establish physical button
actuation.

The separate [native UI check](ui-acceptance.json) used synthesized keyboard
events through the real application's accessibility surface. Screenshots and
application state verified pause and resume, Command-R reset and attract return,
coin input, accelerator confirmation of car selection, a visible Beginner race
with its LAP 1/8 HUD, and Command-Q termination with exit code zero. That run
competed with headless qualification work and recorded five audio underruns and
one backlog recovery. Its result is limited to routing, visible behavior and
lifecycle; it is excluded from cadence and audio acceptance.

The final [live acceptance](live-acceptance.json) passed an isolated 80-second
visible Beginner automatic run on an Apple M3 Ultra running macOS 27.0. It
recorded 4,803 game frames (60.04 per second),
4,805 main-thread display updates and 4,675 presented frame snapshots (58.44 per
second). Native calls remained on the dedicated engine thread; there were no
engine faults, discarded clock gaps, audio-open failures, underruns or backlog
recoveries. The output device was running at 48 kHz with the game's 44.1 kHz
source, rendered PCM counters advanced, and the peak pending queue was 3,998
source sample frames. The report binds the final executable, package, route,
checker and captured image. Presentation counters describe the host's frame
handoff, not a physical display scanout measurement; audio-device counters do
not substitute for subjective listening. The accepted run uses the worker host
and supersedes earlier main-thread presentation profiling.

The [clean reproduction](reproduction-acceptance.json) re-extracted and verified
all 315 original source files, imported the 47-file media set, generated settings,
captured all four routes, regenerated the processors, and built both engines
without importing main-workspace generated code, settings, captures, objects or
libraries. It passed the CPU fixtures, 35 bridge checks, 123 input checks,
typecheck, four negative link checks and package audit. Reviewed source updates
during the run are disclosed in the report; this was not a single untouched
final-source snapshot.

All four reproduced integration routes matched every main-build result row:
22,832 picture/PCM/count frames and 16,781,520 stereo sample frames. The separately
packaged app also passed the full 9,500-frame manual route and two deterministic
2,400-frame fresh sessions in one process. Its fresh four-route capture admitted
251 DSP images, compared with the main development capture's 253 exploratory
images; the reproduced build passed its own 4,016 DSP state/sample-RAM trials and
1,245 execution-limit trials, alongside the same PowerPC, Z80 and 68000 fixture
counts. This establishes the recorded behavioral reproduction. Binary hashes
differ with build paths and fresh generated inputs, so no byte-identical build
claim is made. Live cadence, audio-device and visible UI evidence applies to the
main packaged app; the reproduced package was checked headlessly.

The evidence qualifies the listed build and routes against the selected
reference. It does not establish physical Model 3 hardware equivalence, analog
audio accuracy, physical controller or wheel actuation, force-feedback behavior,
or network/linked-cabinet operation. The target uses a detached single-cabinet
network interface and does not expose force feedback. Unsupported executable
uploads fail explicitly instead of acquiring an unverified runtime execution
path. Local ROMs, NVRAM, generated program arrays, raw traces and screenshots
remain outside the published source inventory.
