# Original application artwork

The application icon is original vector drawing code in
`scripts/build_icon.swift`: a white numeral 2, blue track ribbons, a red speed
stripe and checker accents. It contains no SEGA logo, game capture, ROM data or
copied game artwork. The build draws each required icon resolution directly
and packages the PNGs with Apple's `iconutil`; generated images stay in `build/`.
