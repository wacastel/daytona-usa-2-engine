# Daytona USA 2 for Apple Silicon

A standalone arm64 macOS port of **Daytona USA 2: Battle on the Edge,
Revision A** (`daytona2`), using locally supplied game media and original
USA/single-cabinet settings. The current controller and optional countdown
update passed all four reference/native gameplay routes with assistance off,
dedicated timer checks, packaged-host replay, cold-reset comparison and a live
display/audio check.

The initial release also passed a separate clean-source reproduction, with
recorded source updates during qualification. That reproduction and the older
sound-lifecycle/package-requalification records remain historical evidence;
current-build acceptance uses the reports described below.

The project follows the earlier Daytona USA and Virtua Fighter 2 workflow:
fixed offline translation of every executing processor, a separate original-
processor reference, and a native macOS host. The selected set has 47 files
checked by length, CRC32, SHA-1 and SHA-256. Other supplied revisions and Power
Edition remain untouched. Game media, generated program arrays, captures, saves
and binaries are excluded from Git. No script downloads game media.

Requirements: Apple Silicon, macOS 14 or later, Xcode Command Line Tools
providing Clang and Swift, Python 3.12 or later, and the system curl/tar tools.
The isolated processor fixtures also use SDL2 development headers and
`sdl2-config`. The native host uses AppKit, SpriteKit, AVFoundation and
GameController; the hardware renderer uses macOS OpenGL. The product does not
use the SDL frontend.

The current engine matches the original-processor reference on **22,832
frames and 16,781,520 stereo sample frames**, comparing every picture, PCM block
and sample count with countdown assistance off. The packaged app also matched
the 9,500-frame manual route and
passed two 2,400-frame fresh-session determinism checks. The four engine routes
cover all three courses and both transmission modes, with manual transmission
exercised on Beginner. A separate 80-second
visible run on an Apple M3 Ultra with macOS 27.0 recorded **60.025 game frames/s
and 59.7125 presented frame snapshots/s**, with no engine faults, audio-open
failures, underruns or backlog recovery. The GUI uses a dedicated engine thread
and a main-thread SpriteKit presenter. These measured presentation counters are
not a physical display scanout measurement. See the
[current update record](Documentation/controls-update-acceptance.json) and
[validation record](Documentation/validation.md) for identities, methods and
the precise coverage and limits.

The complete build entry point verifies the pinned source and local media,
recreates the original cabinet settings through the game's service menu,
captures the authored gameplay routes in the isolated observer, compiles fixed
programs, and runs processor, original-reference replay and bridge checks.
Pass `--game` the unpacked Revision A directory containing the 47 canonical ROM
files:

```sh
python3 scripts/prepare_native.py --game '/path/to/daytona2' --jobs 8
python3 scripts/verify_timer.py
scripts/build_host.sh --typecheck
scripts/build_host.sh --self-test
scripts/build_host.sh --test-link-guard
scripts/build.sh --skip-engine
python3 scripts/verify_package.py
python3 scripts/verify_host.py
python3 scripts/verify_host_reset.py
python3 scripts/verify_live.py --seconds 80
```

Run the visible check by itself, with the game window focused and no competing
engine/replay workload. It launches and closes the app automatically. The
package checker validates artifact identities and execution boundaries; the
host checker runs the actual packaged executable against an accepted engine
trace and checks two fresh sessions in one process. These checks serve different
purposes and do not replace one another.

Double-click `Play.command` to open `build/Daytona USA 2.app`; it builds the app
first if absent. Insert coins, press Start, then steer through the original
selection screens and press the accelerator to confirm.
Without `--skip-engine`, `scripts/build.sh` performs the preparation pipeline
using `Daytona USA 2 ROMs/daytona2` as its local media directory.

The application has independent preferences and saves under
`local.william.daytonausa2`. A fresh save directory receives the authenticated
USA/single-cabinet seed made by the original service-menu replay. Existing saves
are preserved. See [cabinet settings](Documentation/cabinet-settings.md).

| Action | DualSense | Keyboard |
| --- | --- | --- |
| Steer | Left stick / D-pad | Left / Right |
| Accelerate | R2 | W / Up |
| Brake | L2 | S / Down |
| Shift up / down | R1 / L1 | E / Q |
| Direct gear / neutral | Sequential selection | 1–4 / N |
| Insert coin | Circle | C |
| Start / resume | Options | Return |
| Next / previous camera | Cross / Square cycles all four views | F1–F4 select directly |
| Close / distant exterior car view | Right stick down / left | F3 / F4 |
| Freeze / unfreeze race countdown | Triangle | T |
| Pause / resume | Create (small button left of the touchpad) | P / Escape |

Right stick up / right selects the forward road / hood view. Repeated presses
of the original hood-view selector also toggle the cockpit view. The exterior
views use original selectors 3 and 4; a tap selects either view and it remains
selected after release. The [camera review](Documentation/camera-acceptance.json)
records this native-engine mapping. Cross and Square reach both exterior views.
L3 has no assigned action. Options remains Start and also resumes a paused app.

Triangle or T toggles optional race countdown assistance. A **TIMER FROZEN**
indicator appears while enabled. Assistance starts off and resets off; driving,
race/lap elapsed time and checkpoint time extensions continue. Switching it off
resumes the original countdown, and enabling it after expiry does not revive
the race. The option acts on an authenticated fixed native operation without
editing ROMs or save files. It is a user-requested gameplay aid, separate from
original-reference parity with assistance disabled.
The [timer check](Documentation/timer-acceptance.json) verifies a 600-frame hold
while elapsed time advances, resumption on release and unchanged expired state.

The current [host input checks](Documentation/host-input-acceptance.json)
passed 149 cases using actual routing code and Apple synthetic gamepads, with
typecheck and four negative link checks. They include camera cycling, held-stick
behavior across independent engine frames, Create pause/resume and timer-toggle
edges. The current [packaged-host check](Documentation/host-acceptance.json)
matched all 9,500 manual-route frames and two fresh 2,400-frame sessions. The
[UI record](Documentation/ui-acceptance.json) separately verifies synthesized
keyboard timer toggles, the visible indicator, pause/resume and mid-race reset
in the final package. Its concurrent run is excluded from live cadence/audio
acceptance and does not establish physical controller actuation.
Focus loss, sleep or assigned-controller disconnection pauses the game and
clears pending driving input. Controls must return to neutral before resuming;
the committed gear is retained.

Reset recreates the engine on its owning thread and reloads the same saved
cabinet state, clearing countdown assistance. The
[reset check](Documentation/host-reset-acceptance.json) verifies 3,000 restarted
frames against a fresh process after 3,060 gameplay frames, including enabled
countdown assistance.

This target supports the selected Revision A single-cabinet game. The accepted
routes exercise bounded racing, camera changes, steering, pedals, collisions,
manual gears, time expiry and subsequent menus; they do not prove completed
races, every car/state, every course/transmission combination or physical
arcade-board equivalence. Physical controller actuation and subjective speaker
listening are not claimed. Linked cabinets and force feedback are not exposed.
Unknown executable uploads stop with an explicit error.

The hardware source is pinned to [Supermodel commit
24d2ffcfc7f14229337f05f4920fe26b56633d9d](https://github.com/trzy/Supermodel/tree/24d2ffcfc7f14229337f05f4920fe26b56633d9d).
Its original source, GPLv3 license and included component notices are preserved.
See [architecture](Documentation/architecture.md) and [source notices](Licenses/README.md).
Repository destinations are the [private personal game
repository](https://github.com/wacastel/daytona-usa-2) and the [public reviewed
source companion](https://github.com/wacastel/daytona-usa-2-engine). Public source
preparation uses an explicit reviewed inventory and scans for supplied media
and generated binary program data.

Original Daytona USA 2 game content © SEGA, 1998. This project is not affiliated
with or endorsed by SEGA or the Supermodel team.
