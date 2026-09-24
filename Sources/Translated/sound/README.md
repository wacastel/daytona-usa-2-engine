# Fixed sound programs

`scripts/compile_sound.py` derives native operations from the verified local
Daytona USA 2 Battle on the Edge sound and MPEG-board programs. It preserves the
pinned Supermodel source tree and emits all ROM-derived material under ignored
`build/generated/sound/`.

The offline compiler selects the Musashi operation and binds encoded register
fields for each aligned program address. The player dispatches by board and
program address. Every instruction and extension word is checked against the
fixed program; mismatches and unknown addresses stop execution. Indexed operands
use fields extracted offline. There is no opcode-to-operation table, runtime
compiler, generic instruction decoder, or fallback path in the generated player.

SCSP DSP programs observed by the separate reference lab are expanded to straight
line operations with literal fields. The player checks the complete DSP program
before execution and preserves the original latched LastStep limit. While that
limit is zero, the original DSP executes no instructions, including while program
bytes are being uploaded. A missing executing program is a hard error, so reference capture coverage
must be extended whenever a new program is discovered.

`scripts/verify_sound.py` separately links the untouched reference and generated
native cores. It compares all distinct ROM opcodes in two machine states,
including registers, flags, cycles, ordered bus reads and writes, and stop state.
For each captured DSP program it compares the full DSP state and sample RAM after
13 samples from 16 randomized initial states, plus partial latched execution limits.
Negative probes prove that changed
opcodes, changed extension words, unknown PCs, and unknown DSP programs are
rejected. Whole-game replay and audio evidence are separate integration checks.

The shared derived SCSP source also resets its sound CPU cycle remainder when a
new board is initialized. The original function-static remainder otherwise
survived game destruction. `Tools/ReferenceLab/sound_lifecycle.py` checks two
fresh game contexts in one process against a preserved first-process replay;
`Documentation/sound-lifecycle-acceptance.json` records the 2,400-frame result.

Reference capture helpers and differential fixtures live in
`Tools/ReferenceLab/sound*`; these are never linked into the player. Generated
source remains subject to Supermodel's GPL notices and the notices retained in
its Musashi implementation. Proprietary ROM bytes and derived tables are not
redistributed in the repository.
