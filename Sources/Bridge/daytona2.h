// GPL-3.0-or-later
#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct daytona2_context daytona2_context;
enum daytona2_button {
 DAYTONA2_COIN=1, DAYTONA2_START=2,
 DAYTONA2_VIEW1=4, DAYTONA2_VIEW2=8, DAYTONA2_VIEW3=16, DAYTONA2_VIEW4=32,
 DAYTONA2_NEUTRAL=64, DAYTONA2_GEAR1=128, DAYTONA2_GEAR2=256,
 DAYTONA2_GEAR3=512, DAYTONA2_GEAR4=1024
};
/* One serialized process-wide session. Independent processes keep separate
 * cabinet state. assets contains canonical daytona2.zip and Games.xml; saves
 * is writable app-owned storage. Every media identity is checked before load.
 */
daytona2_context* daytona2_create(const char* assets,const char* saves);
void daytona2_destroy(daytona2_context*);
int daytona2_reset(daytona2_context*);
/* Optional race-countdown assistance. Defaults off; reset turns it off.
 * Serialized with other context calls. Does not alter laps or elapsed time.
 */
int daytona2_set_timer_frozen(daytona2_context*,int enabled);
int daytona2_timer_frozen(const daytona2_context*);
const char* daytona2_error(const daytona2_context*);
uint32_t daytona2_fault_code(const daytona2_context*);
/* One video interval, steering[-1,1], pedals[0,1], mutually exclusive gear
 * commands. No gear bit retains latched gear. Returns1 on success,0 on error.
 * Buffers remain valid until the next call. RGBA is top-down, tightly packed.
 * PCM is interleaved native-endian signed16 stereo; count is stereo frames.
 */
int daytona2_step(daytona2_context*,float steering,float accelerator,float brake,uint32_t buttons);
const uint8_t* daytona2_pixels(const daytona2_context*);
const int16_t* daytona2_audio(const daytona2_context*);
int daytona2_audio_count(const daytona2_context*);
int daytona2_width(const daytona2_context*);
int daytona2_height(const daytona2_context*);
double daytona2_frame_rate(const daytona2_context*);
int daytona2_audio_sample_rate(const daytona2_context*);
uint64_t daytona2_frame_number(const daytona2_context*);
#ifdef __cplusplus
}
#endif
