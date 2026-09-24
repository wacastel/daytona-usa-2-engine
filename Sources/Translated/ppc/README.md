# Fixed PowerPC and wheel-board execution

`scripts/compile_ppc.py` derives a native executor from the pinned Supermodel
PowerPC semantics. It verifies the four Revision A CROM sockets, interleaves their
halfwords exactly like the source loader, and fixes all supported aligned starts
in the upper 2 MiB program region and the game's corresponding low RAM copy.
Exact original instruction words guard every dispatch. Laboratory observations
can add fixed program variants at other addresses; complete uploaded RAM images
can be supplied with `--ram-image ADDRESS:PATH`. Neither discovery mechanism is
present at runtime. Unknown addresses and changed words throw a host-visible
fault, as do inherited fatal hardware conditions.

The reference replay captures the helper page at `0x0063d000` as a 4 KiB
diagnostic image and separately emits `helper-63d000-code.bin`. The latter stops
at exclusive `0x0063d95c`, immediately after the helper's final return instruction.
Subsequent words are helper data. Native preparation uses the bounded code image;
all executed helper identities are checked against independently captured images
when recording acceptance evidence. Generation fails if any observed word inside
a supplied immutable image differs from that image.

Operations are C++ template instances with the entire encoded instruction bound
at compilation. No operation accepts a runtime opcode. Runtime selection uses
fixed program addresses and checks byte identity, then calls the corresponding
parameterless compiled function. The original timer, interrupt, exception,
register and bus behavior remains. An inherited shift-by-32 expression in the
three rotate operations is made defined at zero shift; otherwise compile-time
specialization exposes undefined behavior that the original dynamic arm64 core
masked. Differential cases cover that zero-shift correction.

`Tools/ReferenceLab/ppc_observer.inc` and generated `ppc-observer.cpp` belong only
to the isolated reference executable. `DAYTONA2_PPC_TRACE` records executed
address/word identities there. Observations, complete uploads, generated native
source and original media stay outside Git. Reference observations demonstrate
coverage only for the exercised paths; a static image adds its entire bounded
set of fixed starts, without establishing physical-board or complete-game
equivalence.

`scripts/compile_z80.py` specializes the supplied `epr-20985.bin` wheel program.
All 36,864 mapped ROM byte starts have exact four-byte guards. Base and prefix
selection and immediate operands are resolved offline; remaining CB switches
have literal selectors and compile away. Original interrupt modes, cached
register behavior, ignored prefixes and inherited HALT behavior are retained.
The product keeps no generic Z80 instruction fetch/decoder.

`scripts/verify_ppc.py` compares fixed arithmetic, branch, floating-point, flag
and bus-write behavior with unchanged upstream operations over varied states.
Its `--observations` and `--ram-image` arguments also include every supplied fixed
upload address/word variant in that differential comparison.
`scripts/verify_z80.py` compares every mapped ROM start over four register and
interrupt states, including the instruction's immediate interrupt boundary.
Full frame/audio replay remains a separate integration requirement. Both cores
and generated derivatives retain the upstream notices and GPL terms.
