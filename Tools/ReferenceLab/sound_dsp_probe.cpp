/* Differential SCSP fixture: same data/memory, independent reference/native. */
#include "SCSPDSP.h"
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>

extern "C" void daytona2_native_fault(const char *message) { std::fprintf(stderr,"%s\n",message); std::abort(); }

static uint32_t next(uint32_t &seed) { seed=seed*1664525u+1013904223u; return seed; }
static uint64_t hash(const void *bytes, unsigned count, uint64_t value=1469598103934665603ULL) {
  const uint8_t *p=(const uint8_t *)bytes;
  for(unsigned i=0;i<count;i++) value=(value^p[i])*1099511628211ULL;
  return value;
}
extern "C" uint64_t sound_dsp_probe_limit(const uint16_t *program, uint32_t seed, unsigned steps, int last_step) {
  static uint16_t ram[0x80000];
  _SCSPDSP dsp;
  SCSPDSP_Init(&dsp);
  dsp.SCSPRAM=ram; dsp.SCSPRAM_LENGTH=sizeof(ram);
  dsp.RBP=next(seed)&127; dsp.RBL=0x8000<<((next(seed)>>10)&3);
  dsp.DEC=next(seed);
  for(auto &x:ram) x=(uint16_t)next(seed);
  for(auto &x:dsp.COEF) x=(int16_t)next(seed);
  for(auto &x:dsp.MADRS) x=(uint16_t)next(seed);
  for(auto &x:dsp.TEMP) x=(int32_t)next(seed)>>8;
  for(auto &x:dsp.MEMS) x=(int32_t)next(seed)>>8;
  for(auto &x:dsp.EXTS) x=(int16_t)next(seed);
  memcpy(dsp.MPRO,program,sizeof(dsp.MPRO));
  SCSPDSP_Start(&dsp);
  if (last_step>=0) dsp.LastStep=last_step;
  for(unsigned i=0;i<steps;i++) {
    for(auto &x:dsp.MIXS) x=(int32_t)next(seed)>>12;
    SCSPDSP_Step(&dsp);
  }
  dsp.SCSPRAM=nullptr;
  return hash(&dsp,sizeof(dsp),hash(ram,sizeof(ram)));
}
extern "C" uint64_t sound_dsp_probe(const uint16_t *program, uint32_t seed, unsigned steps) {
  return sound_dsp_probe_limit(program,seed,steps,-1);
}
