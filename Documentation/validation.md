# Validation evidence

The startup-credit fix changes only the Swift host. Its current package,
packaged-host replay, reset, original-credit analysis and 85 synthetic save-policy
checks are recorded separately from the unchanged engine qualification below.
The [startup UI check](startup-ui-acceptance.json) used an isolated copy of the
affected 13-credit save. Attract mode showed INSERT COIN(S) and CREDIT 0; a
single C key press then entered course selection. The host made an exact backup
and changed one byte before native creation. After normal game execution and
coin insertion, EEPROM and score-table bytes remained identical; only expected
credit, accounting and timing bytes differed. All 3,921 frames were fault-free.
This concurrent test recorded one audio underrun and does not replace isolated
audio/performance qualification.

Earlier UI/live, clean-reproduction and sound-lifecycle reports identify their
original artifacts; they are not fresh tests of the startup fix.

This report records the bounded qualification of Daytona USA 2: Battle on the
Edge, Revision A (`daytona2`) on arm64 macOS, including the v1.1 race-timer assist
and controller changes. Current PowerPC, timer, bridge, input and four-route
reference/native checks, updated packaged-host replay and cold-reset checks
have passed. Earlier controller/timer UI and isolated 80-second live playback
checks also passed for their recorded package. The retained sound, Z80, helper
capture, sound-lifecycle and clean-reproduction evidence identifies its original
builds; those historical runs are not presented as fresh v1.1 qualification.

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
| PowerPC 603R | 1,894 ROM address/operation samples across 157 handler families and all 203 admitted helper starts, each in eight register states: 16,776 comparisons | Exact state and bus-write agreement; unknown address and changed instruction rejected |
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

The initial-release [sound lifecycle check](sound-lifecycle-acceptance.json)
compares two fresh game contexts, each running 2,400 Beginner automatic frames, in one process
across destruction and recreation. Every picture, PCM block and sample count
matches between sessions and against a preserved first-process baseline, with
zero differing frames. The shared derived SCSP initialization clears the
inherited sound-CPU cycle remainder at cold initialization. This preserves
original first-process scheduling; the accepted fixture uses the public C ABI
and does not patch private globals or restart the process between sessions.
That specific library-bound sound test was not rerun for v1.1; the sound sources
and generated programs are unchanged. Current packaged-host lifecycle evidence
is recorded separately below.

The PowerPC helper at `0x0063d000` was independently captured during Advanced,
Expert and manual gameplay. All three executable images match exactly over
2,396 bytes, ending immediately after the return at `0x0063d958`. All executed
PowerPC identities in 15 observation traces match either the verified static
program/RAM alias or that helper image. A separate 4 KiB diagnostic page is
retained locally; data following the executable boundary is excluded from the
admitted helper code. Generation also rejects observations that conflict with
the supplied immutable image. These captures establish the exercised upload
identity, not exhaustive future reachability.

The v1.1 timer assist is a separate, opt-in change to one authenticated fixed
PowerPC countdown operation. Four original ROM contexts bind its decrement,
caller and phase dispatch. The wrapper executes the original operation,
preserving its carry and timing, and holds only the positive result at the
verified PC, base register, active race phase and caller state. Initialization,
other counters and the original following store remain intact. It neither
patches ROM/save data nor adds an instruction decoder. The PowerPC fixture adds
84 complete-state guard/carry comparisons, two changed timer-opcode rejection
checks and four changed-context rejection checks.

The [timer acceptance](timer-acceptance.json) compares 6,700 shipping-native
OFF frames with the original reference and 9,400 shipping-native ON/early
frames with a separately linked, read-only diagnostic library using the same
native product objects. Every RGBA picture, PCM block, sample count and selected
timer flag agrees in its corresponding comparison. The diagnostic library adds
an explicit laboratory marker and exposes only the bridge's existing RAM-read
accessor; original/derived bridge hashes and every reused object are bound.
No diagnostic accessor is exported by the shipping library.

In the controlled braking route, the countdown stays at 2,970 for 600 frames
while the race elapsed counter advances by 600. The next two frames after
disabling the assist resume at 2,969 and 2,968. Expiry occurs exactly 600 frames
later than the original, and enabling after expiry does not revive the race.
Enabling from boot preserves the first 2,250 original boot/menu/pre-race frames
and initial countdown of 3,420. Fresh creation selects OFF and the native reset
API clears the flag; that API assertion does not qualify continued stepping after
a midrace partial reset. The separate host-reset check addresses that boundary.
Invalid/null requests reject, and the original reference rejects enabling assistance. The
checkpoint-extension operations are unchanged, but this controlled timer route
does not prove every extension or finish state.

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
`a4c9076800ad09d79c160c1a55480017f9adb1239d7dd37ffd53742e5973deec`,
the reference library, archive, media, routes and validation sources. These
comparisons were rerun for v1.1 with assistance OFF; all 22,832 result rows
also match the initial-release baseline. Concurrent replay
processes share the GPU, so their elapsed times are not live-application
performance measurements.

The [bridge checks](bridge-acceptance.json) passed 43 real native-engine cases:
media identity, lifecycle, invalid numeric inputs, conflicting gears, unexposed
or unknown input bits, no advancement after rejected input, recovery, reset,
save and recreation, including timer defaults, valid/invalid requests and reset
clearing the assist. The [package audit](package-acceptance.json) also passed:
arm64 executable and native library, macOS 14 deployment target, system-only dependencies,
expected fixed-execution symbols, no matched decoder/diagnostic symbols,
resource/source identities and ad hoc signature. Symbol inspection alone does
not prove execution semantics.

The initial-release [package requalification record](package-requalification.json)
records a historical audit-only change whose 14 application files stayed
byte-identical. That equivalence applies only to the executable and manifests
identified there. The v1.1 package has changed executable bytes and receives its
own package, host, live and UI checks; the old byte-equivalence result is not
being reused for this release.

The current startup-fix [packaged-host check](host-acceptance.json) passed against
executable `4e02ee337cc800ae8088584721da2d1dcdfab8aa9fefe2ad6834940ae1bf22e1`,
whose package audit also passed. Every picture, PCM block and count in the
9,500-frame Beginner manual route matches the accepted direct-engine trace,
covering 6,982,500 stereo sample frames. Two fresh sessions in one process each
ran 2,400 frames and produced identical picture/audio/count identities and
1,764,000 stereo sample frames. The final engine fault code was zero. These
headless checks qualify engine linkage, bundled media and session lifecycle;
they do not exercise the display or output audio device.

The [host-reset qualification](host-reset-acceptance.json) exercises the corrected
reset path: destroy the old game context and create a fresh one on the same
engine thread, retaining the cabinet NVRAM and clearing timer assistance. After
3,060 prerestart frames and 3,000 postrestart frames, every postrestart picture,
PCM block and sample count matches a fresh game using the same NVRAM. This
replaces the host's earlier use of a partial board reset, which could leave an
unadmitted SCSP DSP image after a midrace reset. The fixed program guards remain
intact; no unknown sound program or fallback is admitted to accommodate reset.

The GUI host now owns one persistent engine thread for graphics-context
creation, stepping, reset and destruction. It produces audio independently of
SpriteKit and passes immutable frame snapshots to the main-thread presenter.
The [host input report](host-input-acceptance.json) records 149 passed checks,
including immutable in-flight inputs, retention of later taps, pause/resume and
committed gear behavior. New cases cover Triangle/T edge-triggered timer
selection, Create pause/resume, ignored stick clicks, all-four-view cycling,
direct camera selection and transition/neutral-gating behavior. Those checks
use synthetic Apple controller values and do not establish physical button
actuation.

The [camera investigation](camera-acceptance.json) identified the original
selectors using the initial-release engine: VR1 is a forward road/bumper view;
VR2 alternates hood and cockpit on successive presses; VR3 and VR4 are close and
distant exterior chase views. Their selections persist after release. This
explains why the former fixed Cross/Square mappings reached only VR1/VR2.
The v1.1 input router cycles all four selectors with Cross/Square and retains
right-stick down/left as direct VR3/VR4 selections. Original camera behavior is
supported by that investigation and the unchanged current integration output;
new controller routing is covered by the 149 synthetic input checks. Neither
record claims physical PS5 button actuation.

The earlier controller/timer [native UI check](ui-acceptance.json) used synthesized keyboard events
against its recorded executable, an authored Beginner automatic driving route
and temporary saves. T enabled the yellow indicator; race screenshots showed
the countdown held at 60 while lap elapsed time advanced from 0.00 to 23.40 and
the car continued driving. T again removed the indicator; exact next-step
countdown resumption is separately established by the timer acceptance. P
showed the pause overlay and Return resumed racing. T followed by Command-R
during lap 2 cleared the indicator and restarted the game; final telemetry
recorded 2,672 postreset frames, timer OFF, zero engine faults and native calls
on the dedicated worker. The application exited normally after 150 seconds.

That UI run competed with headless qualification and recorded two audio
underruns, zero discarded clock gaps and zero backlog recoveries. Its accepted
scope is visible behavior, keyboard routing and reset continuation, separate
from isolated cadence/audio acceptance and physical PS5 actuation.

The isolated v1.1 [live acceptance](live-acceptance.json) passed an 80-second
visible Beginner automatic run against its recorded executable. It recorded
4,802 game frames (60.025 per second), 4,804 main-thread display updates and
4,777 presented frame snapshots (59.7125 per second). Native calls stayed on the
dedicated engine thread, with zero engine faults, discarded clock gaps, audio
underruns or backlog recoveries. The audio device opened and ran at 48 kHz with
the game's 44.1 kHz source; rendered PCM counters advanced and the peak pending
queue was 3,939 source sample frames.

That report binds its earlier executable, package, route, checker and captured
image. This run had no competing engine workloads. Presentation counters
describe the host's frame handoff, not physical display scanout; audio-device
counters do not substitute for subjective listening or physical-board audio
accuracy. The old initial-release live metrics are not used to qualify this
changed package.

The initial-release [clean reproduction](reproduction-acceptance.json)
re-extracted and verified all 315 original source files, imported the 47-file media set, generated settings,
captured all four routes, regenerated the processors, and built both engines
without importing main-workspace generated code, settings, captures, objects or
libraries. It passed the CPU fixtures, 35 bridge checks, 123 input checks,
typecheck, four negative link checks and package audit. Reviewed source updates
during the run are disclosed in the report; this was not a single untouched
final-source snapshot.

All four initial-release reproduced integration routes matched every
corresponding main-build result row: 22,832 picture/PCM/count frames and 16,781,520 stereo sample frames. The separately
packaged app also passed the full 9,500-frame manual route and two deterministic
2,400-frame fresh sessions in one process. Its fresh four-route capture admitted
251 DSP images, compared with the main development capture's 253 exploratory
images; the reproduced build passed its own 4,016 DSP state/sample-RAM trials and
1,245 execution-limit trials, alongside the original 16,760 PowerPC, 147,456
Z80 and 15,526 68000 fixture comparisons. This establishes the recorded behavioral reproduction. Binary hashes
differ with build paths and fresh generated inputs, so no byte-identical build
claim is made. Live cadence, audio-device and visible UI evidence applies to the
initial-release main packaged app; the reproduced package was checked headlessly.
This clean generation/build experiment has not been repeated for v1.1 and does
not certify the new timer/controller code or new package identity.

The evidence qualifies the listed build and routes against the selected
reference. It does not establish physical Model 3 hardware equivalence, analog
audio accuracy, physical controller or wheel actuation, force-feedback behavior,
or network/linked-cabinet operation. The target uses a detached single-cabinet
network interface and does not expose force feedback. Unsupported executable
uploads fail explicitly instead of acquiring an unverified runtime execution
path. Local ROMs, NVRAM, generated program arrays, raw traces and screenshots
remain outside the published source inventory.
