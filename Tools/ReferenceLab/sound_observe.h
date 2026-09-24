/* Reference-only program capture. Never link into the fixed player. */
#pragma once
#ifdef __cplusplus
extern "C" {
#endif
extern unsigned daytona2_m68k_board;
void daytona2_sound_observe68k(unsigned board, unsigned pc, unsigned (*read_word)(unsigned));
void daytona2_sound_observe_dsp(const unsigned short *words);
#ifdef __cplusplus
}
#endif
