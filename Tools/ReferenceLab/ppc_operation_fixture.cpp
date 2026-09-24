// Independently compiled with the unchanged original or fixed native PPC core.
#include <cstdio>
#include <cstdarg>
#include <vector>
#include <cmath>
#include <cstring>
#include "FIXTURE_CORE"

static bool timerFrozen = false;
extern "C" bool daytona2_race_timer_frozen() { return timerFrozen; }

void DebugLog(const char *, ...) {}
void InfoLog(const char *, ...) {}
Result ErrorLog(const char *, ...) { return Result::FAIL; }

struct FixtureBus: IBus {
  UINT64 writes=0;
  bool timerState = false;
  UINT8 phase = 17, callerState = 13;
  UINT8 Read8(UINT32 a) override {
    if (timerState && a == 0x105004) return phase;
    if (timerState && a == 0x7350ee) return callerState;
    return UINT8((a*13)^0x5a);
  }
  UINT16 Read16(UINT32 a) override { return UINT16(Read8(a))<<8|Read8(a+1); }
  UINT32 Read32(UINT32 a) override { return UINT32(Read16(a))<<16|Read16(a+2); }
  UINT64 Read64(UINT32 a) override { return UINT64(Read32(a))<<32|Read32(a+4); }
  void Write8(UINT32 a, UINT8 d) override { writes=(writes*0x100000001b3ULL)^a^d; }
  void Write16(UINT32 a, UINT16 d) override { writes=(writes*0x100000001b3ULL)^a^d; }
  void Write32(UINT32 a, UINT32 d) override { writes=(writes*0x100000001b3ULL)^a^d; }
  void Write64(UINT32 a, UINT64 d) override { writes=(writes*0x100000001b3ULL)^a^d; }
};

static void emit(UINT64 value) { std::fwrite(&value, sizeof(value), 1, stdout); }

int main(int argc,char **argv) {
  if(argc!=2)return 2;
  FILE *f=std::fopen(argv[1],"r"); if(!f)return 3;
  FixtureBus bus;
  std::vector<UINT32> memory(0x200000);
  PPC_FETCH_REGION fetch[]={{0,0x7fffff,memory.data()},{0xff800000,0xffffffff,memory.data()},{0,0,nullptr}};
  UINT32 address,word;
  while(std::fscanf(f,"%x %x",&address,&word)==2) {
    for(unsigned seed=0;seed<8;++seed) {
      PPC_CONFIG config={PPC_MODEL_603R,0x25,BUS_FREQUENCY_66MHZ};
      ppc_init(&config); ppc_attach_bus(&bus); ppc_set_fetch(fetch);
      ppc.pc=address;ppc.npc=address+4;ppc_change_pc(ppc.npc);
      ppc.icount=1000;ppc.cur_cycles=1000;ppc.tb_base_icount=1000;ppc.dec_base_icount=1000;
      ppc.msr=0x2000;ppc.lr=0x100;ppc.ctr=seed+1;ppc.xer=seed<<29;
      for(unsigned r=0;r<32;++r) {
        ppc.r[r]=seed==0?0:seed==1?0xffffffffU:0x1020304U*(r+1)^0xf00f00fU*seed;
        ppc.fpr[r].fd=(double(int(r)-16)+0.75)*(seed+1);
      }
      for(unsigned r=0;r<8;++r)ppc.cr[r]=(seed+r)&15;
      bus.writes=0;
#ifdef FIXTURE_NATIVE
      daytona2_ppc_fixed(address,word);
#else
      switch(word>>26) {
        case 19:optable19[(word>>1)&1023](word);break;
        case 31:optable31[(word>>1)&1023](word);break;
        case 59:optable59[(word>>1)&1023](word);break;
        case 63:optable63[(word>>1)&1023](word);break;
        default:optable[word>>26](word);break;
      }
#endif
      for(unsigned r=0;r<32;++r)emit(ppc.r[r]);
      for(unsigned r=0;r<32;++r)emit(ppc.fpr[r].id);
      for(unsigned r=0;r<8;++r)emit(ppc.cr[r]);
      emit(ppc.pc);emit(ppc.npc);emit(ppc.lr);emit(ppc.ctr);emit(ppc.xer);emit(ppc.msr);
      emit(ppc.srr0);emit(ppc.srr1);emit(ppc.fpscr);emit(ppc.fatalError);emit(bus.writes);
    }
  }
  std::fclose(f);
#ifdef FIXTURE_NATIVE
  unsigned rejected=0;
  try { daytona2_ppc_fixed(0x00800000,word); } catch(const std::runtime_error &) { ++rejected; }
  try { daytona2_ppc_fixed(address,word^1); } catch(const std::runtime_error &) { ++rejected; }
  if(rejected!=2)return 5;
  // Compare the complete CPU structure against the original addic semantics,
  // allowing only the selected positive countdown result to remain unchanged.
  unsigned timerChecks = 0;
  for (UINT32 initial : {0U, 1U, 2U, 3420U, 0x7fffffffU, 0x80000000U, 0xffffffffU})
    for (UINT32 carry : {0U, UINT32(XER_CA)})
      for (unsigned guard = 0; guard != 6; ++guard) {
        bus.timerState = true; bus.phase = guard == 4 ? 5 : 17;
        bus.callerState = guard == 5 ? 12 : 13;
        timerFrozen = guard != 1;
        ppc.pc = guard == 2 ? 0x11a30 : 0x1b060;
        ppc.npc = ppc.pc + 4; ppc.r[0] = initial;
        ppc.r[9] = guard == 3 ? 0x730000 : 0x100000;
        ppc.xer = 0x80000055 | carry; ppc.fatalError = false;
        const auto before = ppc;
        ppc_addic<0x3000ffffU>();
        auto expected = ppc;
        if (guard == 0 && INT32(initial) > 0) expected.r[0] = initial;
        ppc = before;
        daytona2_ppc_fixed(ppc.pc, 0x3000ffffU);
        if (std::memcmp(&ppc, &expected, sizeof(ppc))) return 6;
        ++timerChecks;
      }
  if (timerChecks != 84) return 7;
  unsigned timerRejections = 0;
  for (UINT32 changed : {0x30000000U, 0x3000fffeU}) {
    ppc.pc = 0x1b060; ppc.r[0] = 3420; ppc.r[9] = 0x100000;
    timerFrozen = true; bus.phase = 17; bus.callerState = 13;
    try { daytona2_ppc_fixed(ppc.pc, changed); }
    catch (const std::runtime_error &) { ++timerRejections; }
  }
  if (timerRejections != 2) return 8;
#endif
}
