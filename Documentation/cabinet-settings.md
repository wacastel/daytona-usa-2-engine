# Original cabinet settings

First launch uses a locally generated original-game NVRAM seed with **COUNTRY
USA** and **LINK ID SINGLE**. The seed is created through the game's Test Menu by
`scripts/prepare_settings.py`; it is not a patched ROM or a committed binary save.
Existing user saves are retained. The player verifies the generated seed hash
before using it in an empty save directory.

The pinned Supermodel `Docs/README.txt`, section “Daytona USA 2 and Daytona USA 2
Power Edition,” documents the country menu sequence: enter Test mode, hold Start,
then press VR4, VR4, VR2, VR3, VR1, VR3, VR2. The validated sequence selects USA in
Country Assignments. In Game Assignments, Link ID cycles from MASTER through
SLAVE and LIVE to SINGLE. The replay then exits both menus normally, allowing the
game to save its own EEPROM, reboot, and display the original attract scene.

`Configuration/replays/cabinet-setup.json` contains the complete 2,485-frame
sequence. Button bits are Start=2, VR1=4, VR2=8, VR3=16, VR4=32, Test=65536, and
Service=131072. Test and Service are available only to the separate reference lab.
The reproduction uses a newly created save directory and the reference-only
`DAYTONA2_FACTORY_SETTINGS=1` override, so it cannot consume an existing template
or change supplied saves. A bounded original RTC value makes replay preparation
repeatable.

Independent original-menu runs established the EEPROM fields below. Offsets are
relative to the beginning of the 93C46 block payload; words are stored in host
little endian by the pinned original save implementation. Field copies agree.

| Original setting | 93C46 word indices | Factory JAPAN / MASTER | USA / MASTER | USA / SINGLE |
| --- | --- | --- | --- | --- |
| Country fields | `0x06`, `0x23` | `0x0001` | `0x0002` | `0x0002` |
| Country fields | `0x0c`, `0x29` | `0x0100` | `0x0200` | `0x0200` |
| Link fields | `0x0f`, `0x2c` | `0x0100` | `0x0100` | `0x0000` |
| Stored checksum | `0x03` | `0x854a` | `0xdc6e` | `0x32ca` |

The generator checks the original `M3SEGA` signature, every listed USA/SINGLE
field, the stored checksum value, and the SHA-256 of all 128 EEPROM bytes:
`7e4c41b6d4b63efb5b505250151f6cf3b8c59111c74efed94fd36f321cdcdb37`.
This validates the exact original EEPROM image; the checksum algorithm has not
been inferred or replaced. Backup RAM remains exactly as saved by the original
game. The reproduction also requires nonzero original audio and a rendered
attract frame with more than 256 distinct colors.

Evidence is retained under ignored `build/settings/`: factory-to-USA/MASTER and
USA/SINGLE comparisons, Test Menu screenshots, the successful 3D attract capture,
and each preparation run's trace, screenshots, and NVRAM. The latest validation
report is `build/settings/prepared.json`. The generated seed, asset identity row,
and C++ identity header live under ignored `build/`.
