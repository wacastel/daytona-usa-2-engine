# Native target and source boundaries

The selected game is Daytona USA 2: Battle on the Edge, Revision A (`daytona2`).
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
register, interrupt, exception, bus and device semantics remain. Details and
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
shared host adaptations, not an untouched upstream application.

The shared derived SCSP source resets its sound-CPU cycle overrun at board
initialization. The upstream function-static overrun otherwise survives a
destroy/create boundary. Two fresh 2,400-frame sessions now agree exactly with
each other and the pre-fix first-session baseline; no PRNG reset or instruction
semantics change is used.

`scripts/prepare_native.py` recreates the settings seed, captures all four route
program identities, regenerates the fixed processors, builds native/reference
libraries, runs CPU fixtures, integration comparisons and bridge validation,
and prepares source notices. Native boot and original USA/single-cabinet startup
work. Four routes across all three courses agree with the reference on every
picture, PCM block and sample count over 22,832 frames. The live packaged host
has separately passed an 80-second presentation and audio-device check. The
[validation record](validation.md) distinguishes these bounded results from
complete-game or physical-board accuracy claims.

## macOS host

The narrow `daytona2_*` C ABI owns one engine context, serializes one interval per
step, accepts bounded steering/pedals and mutually exclusive absolute gear
requests, and returns 496×384 top-down RGBA plus interleaved signed 16-bit stereo
PCM. The bridge reports 60 steps per second and 44,100 audio samples per second.
The host displays the picture at 4:3 and queries engine rates.

AppKit, SpriteKit, AVFoundation and GameController provide the window, display,
audio and input. Preferences and normal saves use `local.william.daytonausa2`;
diagnostic runs default to temporary saves. Focus loss, sleep and assigned-pad
disconnection pause the host and clear pending driving input. Committed gear
selection survives pauses. Reset returns the host selector to neutral.

One dedicated thread owns native context creation, every engine step, reset and
destruction, keeping the CGL context on that same thread. It produces audio at
the engine cadence and publishes immutable latest-frame snapshots. SpriteKit's
main-thread update only polls controls and prepares a new texture, so expensive
3D readback cannot batch several game frames into one presentation update.
Input reservation atomically consumes the pending taps for one imminent frame;
later events remain pending. Pause permits that single in-flight frame to finish
but discards its PCM if the pause occurred before publication. Reset and shutdown
wait for the engine thread without making synchronous calls to the main queue.

Headless replay uses the real linked engine. It accepts sequential steps or
ordered half-open event ranges, respecting the explicit route duration including
neutral tails. It records per-frame picture/PCM hashes and counts; the aggregate
framed-audio hash also includes every block length. Host self-tests use the real
input router without an engine stub. Synthetic controller checks qualify routing,
not actual controller button actuation. GUI/audio observations and real-time
throughput require separate evidence from headless replay.

## Packaging and publication

Packaging rejects reference, diagnostic or test-marked archives. It checks the
native build manifest, archive, compiled/generated source and header identities,
CPU manifests, local media and notices. Host source and packaging fingerprints
are recorded across compilation. `scripts/verify_package.py` checks the actual
arm64 executable and native library, deployment target, system-only dependencies,
known decoder/diagnostic symbol boundaries, fixed-execution symbols, resource
identities, source provenance and ad hoc signature. A symbol audit is not proof
of all execution semantics. Gameplay and live-host acceptance remain separate.

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
