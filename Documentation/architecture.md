# Native target and source boundaries

The selected game is Daytona USA 2: Battle on the Edge, Revision A (`daytona2`).
The controller and optional countdown engine retains its qualified processor,
timer and integration results. The startup-credit fix changes only the Swift
host save policy; its package, host replay, reset and startup checks bind the new
host. Earlier live/UI, clean-reproduction, sound-lifecycle and package-requalification
records identify their original artifacts and do not bind the updated app.

`Configuration/media.json` records 47 canonical file identities. The importer
validates the supplied directory and creates a deterministic local ZIP plus a
single-game `Games.xml`; the original supplied directories remain untouched.
The prepared bundle also contains `default.nv`, a settings seed produced through
the original service menu. Its USA/single-cabinet state is checked against the
expected EEPROM identity. [Cabinet settings](cabinet-settings.md) describes the
replay and validation. Existing user saves are never replaced by this seed.

The bundle's media manifest records the exact SHA-256 and length of each local
file. The Swift host verifies every entry, and the C bridge independently checks
compile-time canonical identities before loading the ZIP, XML and fresh-save
seed. None of these game-derived binary files is staged for source publication.

## Pinned hardware source

Supermodel commit `24d2ffcfc7f14229337f05f4920fe26b56633d9d` provides the board,
renderer, sound devices and original processor semantics. Its source archive
has SHA-256 `027c544e0eb223831c3a702fe326f7ac7c9b120c036133f05b52ccf3ca0feb95`.
`scripts/prepare_source.py` verifies every one of its 315 original files, file
inventory and executable flags. It supports the existing untouched Git clone
and a fresh archive extraction. Git metadata is outside the byte comparison.
No original upstream source is edited in place.

The build places hardware adaptations under `build/derived/` and CPU/program
output under `build/generated/`. Both are ignored. The single-cabinet target uses
a detached network interface and single-threaded frame execution. The retained
renderer composites into a native offscreen framebuffer, checks the actual
depth attachment, and uses the original viewport/scissor bounds. The bridge
samples the boot clock once, then advances it at game-frame boundaries in UTC.
Laboratory runs fix that clock to the same epoch for reproducible comparisons.
These host adaptations apply to both reference and native engine builds.

The target retains the upstream rendering and board abstractions. It does not
expose linked-cabinet play or wheel force feedback. Those omissions remain
distinct from processor-translation qualification.

## Processor execution and reference boundary

The native engine replaces PowerPC 603R, both Musashi 68000 board contexts,
wheel-board Z80, and SCSP effects-DSP instruction execution with programs
specialized offline from verified original media and captured upload identities.
Runtime dispatch selects a compiled entry by original address and compares its
expected instruction identity. Changed or unknown instructions fail closed.
The shipping target has no original opcode decoder, just-in-time compilation or
interpreter fallback. Generated sources and CPU manifests are fingerprinted in
the engine build manifest.

The PowerPC generator includes supported starts in the static program, its
RAM alias and the authenticated uploaded helper. Z80 execution covers every
mapped ROM byte start. The sound compiler binds operation fields and extension
words, and expands admitted SCSP programs into fixed operations. The original
register, interrupt, exception, bus and device semantics remain with optional
countdown assistance disabled. Details and
bounded fixture coverage are documented in [PowerPC/Z80](../Sources/Translated/ppc/README.md)
and [sound](../Sources/Translated/sound/README.md). Uploaded-program observations
establish coverage of exercised paths, not complete-game reachability.

Original processor execution remains in separately marked `reference` and
`observer` laboratory builds. They use the same retained hardware/rendering and
frame boundary as the native target. Authored replay routes compare every RGBA
frame, PCM block and stereo-frame count in independent processes with fresh
isolated saves. Synthetic processor fixtures and negative instruction guards
complement those integration comparisons. Reference parity is not physical-board
equivalence, and the reference is an original-processor build with the stated
shared host adaptations, not an untouched upstream application. Original-reference
parity comparisons run with countdown assistance disabled; the reference build
rejects enabling that option.

The user-requested countdown option is implemented at one authenticated fixed
PowerPC operation for this Revision A program. Its original PC and instruction
identity, active race phase and caller state guard the substitution. When
enabled with positive remaining time, it retains that countdown result while
preserving the operation's original carry behavior and scheduling. Menu and
pre-race initialization, elapsed race/lap time and checkpoint time extensions
remain original. Disabling it resumes the next original decrement; enabling it
after expiry does not revive the race. The option performs no ROM or save-file
edits and introduces no decoder, runtime compiler or interpreter fallback.
The [PowerPC record](ppc-acceptance.json) binds its exact guards and passes
16,776 ordinary state comparisons plus 84 complete-state countdown cases.
The [timer record](timer-acceptance.json) compares 6,700 disabled frames with the
original reference and 9,400 enabled frames with a read-only lab using product
objects. It verifies a 600-frame hold with 600 elapsed-time increments and an
exact 600-frame delay to expiry after release, alongside initialization and
late-enable checks. It does not exercise every checkpoint, course or finish state.

The shared derived SCSP source resets its sound-CPU cycle overrun at board
initialization. The upstream function-static overrun otherwise survives a
destroy/create boundary. The initial-release
[sound lifecycle record](sound-lifecycle-acceptance.json) established exact
agreement between two fresh 2,400-frame sessions and the pre-fix first-session
baseline; no PRNG reset or instruction semantics change is used. That historical
record does not bind the controller/timer update's new artifacts.

`scripts/prepare_native.py` recreates the settings seed, captures all four route
program identities, regenerates the fixed processors, builds native/reference
libraries, runs CPU fixtures, integration comparisons and bridge validation,
and prepares source notices. Current native boot and original USA/single-cabinet
startup pass, and four routes across all three courses agree with the reference
on every picture, PCM block and sample count over 22,832 frames with assistance
off. The earlier controller/timer package separately passed an 80-second
presentation and audio-device check. The initial release's separate clean build reproduced its
bounded gameplay and packaged-host results; that older reproduction does not
claim a fresh reconstruction of this update. The
[validation record](validation.md) distinguishes these bounded results from
complete-game or physical-board accuracy claims.

## macOS host

The narrow `daytona2_*` C ABI owns one engine context, serializes one interval per
step, accepts bounded steering/pedals and mutually exclusive absolute gear
requests, and returns 496×384 top-down RGBA plus interleaved signed 16-bit stereo
PCM. The bridge reports 60 steps per second and 44,100 audio samples per second.
The host displays the picture at 4:3 and queries engine rates.
The current [bridge acceptance](bridge-acceptance.json) passes 43 native-engine
lifecycle, media, input-boundary and timer-option checks.

AppKit, SpriteKit, AVFoundation and GameController provide the window, display,
audio and input. Preferences and normal saves use `local.william.daytonausa2`;
diagnostic runs default to temporary saves. Focus loss, sleep and assigned-pad
disconnection pause the host and clear pending driving input. Committed gear
selection survives pauses. Reset returns the host gear selector to neutral,
camera selector to view 1 and countdown assistance to off.

On a new interactive launch, after media verification and before native context
creation, the host parses the existing NVRAM and clears only its unused primary
credit byte. An exact SHA-named backup is verified first; malformed saves reject
without modification. EEPROM, records, accounting and the adjacent credit bank
remain intact. This desktop-session policy prevents restored credits from
automatically starting selection in the original USA/SINGLE game. In-session
reset and headless/replay inputs retain their original save semantics. See the
[startup analysis](startup-credit-analysis.json) and
[host policy checks](startup-host-acceptance.json). The
[packaged startup check](startup-ui-acceptance.json) confirms attract mode and
normal keyboard coin insertion with the affected save copy.

Cross and Square select the next and previous original camera selector across
all four views. Right-stick up/right/down/left and F1–F4 select views directly;
down/view 3 is close exterior chase, and left/view 4 is distant exterior chase.
The [camera review](camera-acceptance.json) establishes those original input
semantics using the accepted initial-release native engine, including persistence
after a one-frame tap. It does not qualify the new host routing. Create toggles
pause/resume, Options sends Start or resumes a paused host, and L3 is unassigned.
Triangle/T toggles countdown assistance once per press during active input;
the visible TIMER FROZEN indicator shows its enabled state. The option starts
off, is not persisted, and reset clears it.

One dedicated thread owns native context creation, every engine step, reset and
destruction, keeping the CGL context on that same thread. It produces audio at
the engine cadence and publishes immutable latest-frame snapshots. SpriteKit's
main-thread update only polls controls and prepares a new texture, so expensive
3D readback cannot batch several game frames into one presentation update.
Input reservation atomically consumes the pending taps for one imminent frame;
later events remain pending. Pause permits that single in-flight frame to finish
but discards its PCM if the pause occurred before publication. Reset and shutdown
wait for the engine thread without making synchronous calls to the main queue.

Host reset destroys and recreates the native context on that same dedicated
thread, saving and reloading the existing NVRAM directory. A CPU-only reset can
leave an unsupported intermediate sound/DSP program during a mid-race restart;
the host therefore starts fresh device contexts. The
[reset acceptance](host-reset-acceptance.json) runs 3,060 frames, including 60
with countdown assistance enabled, then verifies frame zero and assistance off
after recreation. Its next 3,000 RGBA/PCM/count frames exactly match an independent
fresh-process boot using the copied saved NVRAM, with no engine fault.

Headless replay uses the real linked engine. It accepts sequential steps or
ordered half-open event ranges, respecting the explicit route duration including
neutral tails. It records per-frame picture/PCM hashes and counts; the aggregate
framed-audio hash also includes every block length. Host self-tests use the real
input router without an engine stub. Synthetic controller checks qualify routing,
not actual controller button actuation. GUI/audio observations and real-time
throughput require separate evidence from headless replay.

The current [input qualification](host-input-acceptance.json) passes 149 router
checks, including held-stick behavior when multiple engine frames occur between
display polls. The [packaged-host replay](host-acceptance.json) matches the
9,500-frame manual route and two deterministic 2,400-frame sessions. The earlier
controller/timer [visible UI check](ui-acceptance.json) observes timer freeze with the lap clock
advancing, timer release, pause/resume and a mid-race reset followed by 2,672
fault-free frames with assistance off. That concurrent UI run recorded two
audio underruns and is excluded from isolated cadence/audio acceptance.

The controller/timer release's [isolated live check](live-acceptance.json) records 4,802 game frames,
4,777 presented snapshots and 4,804 display updates over 80 seconds: 60.025 game
frames/s and 59.7125 presented snapshots/s. There are no engine faults, audio-open
failures, underruns, discarded clock gaps or backlog recoveries; the 48 kHz
output device's peak pending queue is 3,939 source sample frames. These are
host presentation and audio-device counters, not physical scanout or subjective
listening measurements.

## Packaging and publication

Packaging rejects reference, diagnostic or test-marked archives. It checks the
native build manifest, archive, compiled/generated source and header identities,
CPU manifests, local media and notices. Host source and packaging fingerprints
are recorded across compilation. `scripts/verify_package.py` checks the actual
arm64 executable and native library, deployment target, system-only dependencies,
known decoder/diagnostic symbol boundaries, fixed-execution symbols, resource
identities, source provenance and ad hoc signature. A symbol audit is not proof
of all execution semantics. Gameplay and live-host acceptance remain separate.
The retained [package requalification](package-requalification.json) concerns
byte-identical initial-release app files after an auditor-only change. It is
historical. The startup fix has new package, host, reset and startup reports;
controller/countdown UI and live reports remain bound to their earlier executable.

`scripts/prepare_licenses.py` preserves the original GPLv3 document and manual,
embedded copyright/license comments and the original Musashi copyright strings.
The notices retain their exact source bytes with source paths and extraction
ranges recorded in `Licenses/manifest.json`.

`scripts/prepare_publication.py` stages an explicit reviewed source inventory and
checks supplied ROM/archive identities, decoded ZIP/7z members, the settings seed
and local binary program images against complete raw, contiguous hexadecimal and
base64 forms. It also checks source extensions, UTF-8, local user paths and common
credential patterns. Generated program arrays and build trees are excluded by
inventory. This bounded scan is not a general copyright or secret classifier.
The script does not commit, push or publish anything, and its success does not
establish an independent clean rebuild or completed game.
