# Daytona USA 2 macOS host

Standalone AppKit/SpriteKit frontend for the fixed native Daytona USA 2 engine.
The host calls the `daytona2_*` C ABI; it contains no CPU implementation or
fallback engine. Video is 496×384 RGBA presented at 4:3, with the engine's
queried frame rate and signed 16-bit stereo PCM sample rate.

The GUI owns one persistent engine thread for CGL creation, steps, reset and
destruction. It clocks audio independently of SpriteKit and hands immutable
latest-frame snapshots to the main-thread presenter. Input is reserved under
the same routing lock used by UI events; later taps survive an in-flight frame.
Each worker iteration drains an autorelease pool for long sessions.

`scripts/build_host.sh --typecheck` checks the real host. `--self-test` runs the
input router with Apple synthetic gamepads and no engine. `--test-link-guard`
checks rejection of test, reference and diagnostic engines plus failed symbol
inspection. These tests do not establish physical controller actuation.

`scripts/build.sh --skip-engine` packages an already verified native archive.
It checks engine source hashes, exact media identity, licenses and signing.
The bundle contains `Resources/Media/daytona2.zip`, `Games.xml` and
`media-identity.json`. Both the host and native engine check media integrity.
An optional verified `default.nv` supplies original cabinet settings for a fresh
save directory; existing saves remain owned by the engine and user.
The host uses `local.william.daytonausa2` for preferences and normal saves.
Diagnostic runs default to temporary saves. `--assets` and `--save-dir` provide
explicit overrides; equivalent environment variables are
`DAYTONA_USA_2_ASSET_DIR` and `DAYTONA_USA_2_SAVE_DIR`.

Headless replay and self-test modes execute the real linked engine, recording
picture and PCM digests. The framed audio digest includes every block length.
Use `--help` for replay, capture, bounded GUI and audio telemetry options.
Replay accepts either sequential `steps` or laboratory `events` with half-open
`start`/`end` frame ranges. Active event fields merge in file order, matching
the laboratory replay driver. A top-level `frames` count includes any neutral
tail after the last event; events must fit within that declared duration.

| Action | DualSense | Keyboard |
| --- | --- | --- |
| Steer | Left stick or D-pad | Left / Right |
| Accelerate | R2 | W / Up |
| Brake | L2 | S / Down |
| Shift up / down | R1 / L1 | E / Q |
| Direct gear / neutral | Sequential selection | 1–4 / N |
| Insert coin | Circle | C |
| Start / resume | Options | Return |
| Camera views | Right-stick directions; Cross / Square for 1 / 2 | F1–F4 |
| Pause | L3 | P / Escape |

Focus loss, sleep and active-controller disconnection pause the app and clear
driving input. Connected controls must return to neutral before resuming.
Committed gears survive a pause; resetting returns the host selector to neutral.
Short button taps survive display polls that produce no engine frame.
