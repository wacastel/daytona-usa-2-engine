// Laboratory single-instruction comparison; never compiled into the product.
#include <cstdio>
#include <cstdarg>
#include <stdexcept>
#include "Supermodel.h"
#include "CPU/Bus.h"
#include "BlockFile.h"
#define private public
#include "CPU/Z80/Z80.h"
#undef private
#include "FIXTURE_CORE"

void DebugLog(const char *, ...) {}
void InfoLog(const char *, ...) {}
Result ErrorLog(const char *, ...) { return Result::FAIL; }

struct FixtureBus: IBus {
  UINT8 rom[0x10000]{};
  UINT8 ram[0x2000]{};
  UINT64 writes=0;
  UINT8 Read8(UINT32 a) override { return a<0x9000?rom[a]:a>=0xe000?ram[a&0x1fff]:0xff; }
  void Write8(UINT32 a,UINT8 d) override {
    if(a>=0xe000)ram[a&0x1fff]=d;
    writes=(writes*0x100000001b3ULL)^a^d;
  }
  UINT8 IORead8(UINT32 a) override { return UINT8(a^0xa5); }
  void IOWrite8(UINT32 a,UINT8 d) override { writes=(writes*0x100000001b3ULL)^a^d^0x80000000U; }
};
static void emit(UINT64 value) { std::fwrite(&value,sizeof(value),1,stdout); }
int main(int argc,char **argv) {
  if(argc!=2)return 2;
  FixtureBus bus;
  FILE *f=std::fopen(argv[1],"rb");if(!f)return 3;
  if(std::fread(bus.rom,1,sizeof(bus.rom),f)!=sizeof(bus.rom))return 4;
  std::fclose(f);
  CZ80 cpu;cpu.Init(&bus,nullptr);
  for(unsigned pc=0;pc<0x9000;++pc)for(unsigned seed=0;seed<4;++seed) {
    cpu.Reset();
    cpu.pc=pc;cpu.sp=0xff80;cpu.ix=0xe300;cpu.iy=0xe500;
    cpu.regs[0]={UINT16(1+seed),UINT16(0xe200+seed),UINT16(0xe100+seed)};
    cpu.regs[1]={UINT16(2+seed),UINT16(0xe500+seed),UINT16(0xe300+seed)};
    cpu.af[0]=0x8100|seed*0x55;cpu.af[1]=0x7000|seed*0x35;
    cpu.im=seed%3;cpu.iff=seed&3;cpu.intLine=seed==2;cpu.nmiTrigger=seed==3;
    for(unsigned i=0;i<sizeof(bus.ram);++i)bus.ram[i]=UINT8(i*13+seed);
    bus.writes=0;
    int cycles=cpu.Run(1);
    emit(cycles);emit(cpu.pc);emit(cpu.sp);emit(cpu.ix);emit(cpu.iy);emit(cpu.ir);
    emit(cpu.af[0]);emit(cpu.af[1]);emit(cpu.af_sel);emit(cpu.regs_sel);
    for(unsigned i=0;i<2;++i){emit(cpu.regs[i].bc);emit(cpu.regs[i].de);emit(cpu.regs[i].hl);}
    emit(cpu.iff);emit(cpu.im);emit(cpu.intLine);emit(cpu.nmiTrigger);emit(bus.writes);
  }
#ifdef FIXTURE_NATIVE
  unsigned rejected=0;
  cpu.Reset();cpu.pc=0x9000;
  try { cpu.Run(1); } catch(const std::runtime_error &) { ++rejected; }
  cpu.Reset();bus.rom[0]^=1;
  try { cpu.Run(1); } catch(const std::runtime_error &) { ++rejected; }
  if(rejected!=2)return 5;
#endif
}
