# Daytona USA 2 for Apple Silicon

A standalone arm64 macOS port of **Daytona USA 2: Battle on the Edge,
Revision A** (`daytona2`), using locally supplied game media and original
USA/single-cabinet settings. All four reference/native gameplay routes,
packaged-host headless parity and the final live display/audio check have
passed. A separate clean-source build, with recorded source updates during
qualification, also passed the same gameplay and packaged-host checks.

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

The accepted engine matches the original-processor reference on **22,832
frames and 16,781,520 stereo sample frames**, comparing every picture, PCM block
and sample count. The packaged app also matched the 9,500-frame manual route and
passed two 2,400-frame fresh-session determinism checks. The four engine routes
cover all three courses and both transmission modes, with manual transmission
exercised on Beginner. A separate 80-second
visible run on an Apple M3 Ultra with macOS 27.0 recorded **60.04 game frames/s
and 58.44 presented frame snapshots/s**, with no engine faults, audio-open
failures, underruns or backlog recovery. The GUI uses a dedicated engine thread
and a main-thread SpriteKit presenter. These measured presentation counters are
not a physical display scanout measurement. See the
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
scripts/build_host.sh --typecheck
scripts/build_host.sh --self-test
scripts/build_host.sh --test-link-guard
scripts/build.sh --skip-engine
python3 scripts/verify_package.py
python3 scripts/verify_host.py
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
| Camera views | Right-stick directions; Cross / Square for 1 / 2 | F1–F4 |
| Pause | L3 | P / Escape |

The [host input checks](Documentation/host-input-acceptance.json) passed all 123
cases using actual routing code and Apple synthetic gamepads. The host typecheck
and four negative link checks also pass.
Automated native keyboard actions separately verified pause, resume, reset,
selection, visible racing and clean quit; see the [UI record](Documentation/ui-acceptance.json).
Focus loss, sleep or assigned-controller disconnection pauses the game and
clears pending driving input. Controls must return to neutral before resuming;
the committed gear is retained.

This target supports the selected Revision A single-cabinet game. The accepted
routes exercise bounded racing, camera changes, steering, pedals, collisions,
manual gears, time expiry and subsequent menus; they do not prove completed
races, every car/state, every course/transmission combination or physical
arcade-board equivalence. Physical controller actuation and subjective speaker
listening are not claimed. Linked cabinets, force feedback and timer assistance
are not exposed. Unknown executable uploads stop with an explicit error.

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
