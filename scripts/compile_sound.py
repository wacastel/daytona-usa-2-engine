#!/usr/bin/env python3
"""Offline Daytona USA 2 sound-program specialization from local licensed media.

Generated ROM-dependent C and observations stay under ignored build/. Musashi's
operation selection is performed here, never by the native player. SCSP programs
are emitted as straight-line constant operations from reference captures.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'build/upstream/supermodel'
MUSASHI = SOURCE / 'Src/CPU/68K/Musashi'
ROM_NAMES = ('epr-20865.21', 'epr-20886.ic2')
ROM_SHA256 = (
    '86432fee7e1b7b2d9b2d8475cc2f36a5bcf64bfaa3fb2bfe2e818631cb614bdd',
    '3d6b04bf8e0a1527f7f7dc4888d0d409745fe4acd8acc09e195079ffce54a64c',
)


def sha(data):
    if isinstance(data, Path): data = data.read_bytes()
    if isinstance(data, str): data = data.encode()
    return hashlib.sha256(data).hexdigest()


def replace_function(source, signature, body):
    start = source.index(signature)
    opening = source.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[:opening] + '{\n' + body + '\n}' + source[end:]


def captures(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def build_musashi(output, rom_dir, observations):
    out = output / 'musashi'
    out.mkdir(parents=True, exist_ok=True)
    original = output / 'musashi-original'
    original.mkdir(exist_ok=True)
    subprocess.run(['cc','-O2',str(MUSASHI/'m68kmake.c'),'-o',str(output/'m68kmake')],check=True)
    subprocess.run([str(output/'m68kmake'),str(original),str(MUSASHI/'m68k_in.c')],check=True,stdout=subprocess.DEVNULL)
    # Reproduce the original table-builder's overwrite order offline.
    table = [('m68k_op_illegal',0)] * 65536
    rows = re.findall(r'\{(m68k_op_\w+)\s*,\s*0x([0-9a-f]+),\s*0x([0-9a-f]+),\s*\{\s*(\d+),\s*\d+,\s*\d+\}\}', (original/'m68kops.c').read_text())
    assert len(rows) == 1962, len(rows)
    for name,mask,match,cycles in rows:
        mask,match,cycles = int(mask,16),int(match,16),int(cycles)
        free = (~mask)&65535
        sub = 0
        while True:
            word = match | sub
            extra = 2*(((word >> 9)&7) or 8) if mask == 0xf1f8 and (word&0xf000)==0xe000 and not word&0x20 else 0
            table[word] = (name,cycles+extra)
            sub = (sub-free)&free
            if not sub: break
    functions = {}
    for name in ('m68kopac.c','m68kopdm.c','m68kopnz.c'):
        pp = subprocess.check_output(['cc','-E','-P','-I'+str(MUSASHI),'-I'+str(SOURCE/'Src/OSD/SDL'),str(original/name)],text=True)
        functions.update(re.findall(r'void (m68k_op_\w+)\(void\)\s*\{(.*?)\n\}',pp,re.S))
    assert len(functions) == 1962, len(functions)
    roms = []
    identities = []
    for name,expected in zip(ROM_NAMES,ROM_SHA256):
        path = rom_dir / name
        raw = path.read_bytes()
        assert len(raw)==0x20000, (name,len(raw))
        assert sha(raw)==expected, f'Wrong revision or damaged sound program: {name}'
        roms.append([int.from_bytes(raw[i:i+2],'little') for i in range(0,len(raw),2)])
        identities.append({'name':name,'bytes':len(raw),'sha256':sha(raw)})
    extra_words = {}
    for item in observations:
        if item['kind'] != 'm68k': continue
        board, pc = item['board'],item['pc']
        for i, word in enumerate(item['words']):
            addr = (pc+2*i)&0xffffff
            if board == 0 and 0x600000 <= addr < 0x700000:
                offset=(addr-0x600000)&0x7ffff
                assert word==(roms[0][offset//2] if offset<0x20000 else 0), (board,hex(addr),word)
                continue
            if board == 1 and addr < 0x20000:
                assert word==roms[1][addr//2], (board,hex(addr),word)
                continue
            key=(board,addr)
            if key in extra_words and extra_words[key] != word:
                raise RuntimeError(f'Mutable captured sound code {key}: {extra_words[key]:04x}/{word:04x}; requires explicit program variants')
            extra_words[key] = word
    words = sorted(set(roms[0]+roms[1]+list(extra_words.values())+[0]))
    bodies = {}
    word_function = {}
    for word in words:
        body = functions[table[word][0]].replace('m68ki_cpu.ir',f'0x{word:04x}U')
        # The preprocessor expanded DX/DY/AX/AY and addressing macros, so every
        # opcode-derived operand/register selector is now a literal expression.
        key = sha(body)
        if key not in bodies: bodies[key] = (f'daytona2_sound_op_{len(bodies):05d}',body)
        word_function[word] = bodies[key][0]
    header = (MUSASHI/'m68kcpu.h').read_text()
    interface = '''
/* Offline-bound program entries; lookup uses board and instruction address. */
typedef struct daytona2_sound_entry {
    void (*operation)(void);
    unsigned short word;
    unsigned char cycles, index_register, index_long;
    signed char displacement;
} daytona2_sound_entry;
extern unsigned daytona2_m68k_board;
extern unsigned daytona2_m68k_current_cycles;
const daytona2_sound_entry *daytona2_sound_entry_at(unsigned pc);
void daytona2_sound_fault(unsigned pc, unsigned actual, unsigned expected);
'''
    pos = header.index('/* Handles all immediate reads')
    header = header[:pos] + interface + '\n' + header[pos:]
    header = replace_function(header,'INLINE uint m68ki_read_imm_16(void)\n{', '''
    unsigned pc = ADDRESS_68K(REG_PC);
    const daytona2_sound_entry *entry = daytona2_sound_entry_at(pc);
    unsigned actual = m68k_read_immediate_16(pc);
    if (actual != entry->word) daytona2_sound_fault(pc, actual, entry->word);
    m68ki_set_fc(FLAG_S | FUNCTION_CODE_USER_PROGRAM);
    m68ki_check_address_error(REG_PC, MODE_READ, FLAG_S | FUNCTION_CODE_USER_PROGRAM);
    REG_PC += 2;
    return entry->word;''')
    header = replace_function(header,'INLINE uint m68ki_read_imm_32(void)\n{', '''
    unsigned pc = ADDRESS_68K(REG_PC);
    const daytona2_sound_entry *high = daytona2_sound_entry_at(pc);
    const daytona2_sound_entry *low = daytona2_sound_entry_at(ADDRESS_68K(pc+2));
    unsigned expected = ((unsigned)high->word << 16) | low->word;
    unsigned actual = m68k_read_immediate_32(pc);
    if (actual != expected) daytona2_sound_fault(pc, actual, expected);
    m68ki_set_fc(FLAG_S | FUNCTION_CODE_USER_PROGRAM);
    m68ki_check_address_error(REG_PC, MODE_READ, FLAG_S | FUNCTION_CODE_USER_PROGRAM);
    REG_PC += 4;
    return expected;''')
    header = replace_function(header,'INLINE uint m68ki_get_ea_ix(uint An)\n{', '''
    const daytona2_sound_entry *entry = daytona2_sound_entry_at(ADDRESS_68K(REG_PC));
    unsigned index;
    (void)m68ki_read_imm_16();
    index = REG_DA[entry->index_register];
    if (!entry->index_long) index = MAKE_INT_16(index);
    return An + index + entry->displacement;''')
    header = header.replace('CYC_INSTRUCTION[REG_IR]','daytona2_m68k_current_cycles')
    (out/'m68kcpu.h').write_text(header)
    core = (MUSASHI/'m68kcpu.c').read_text()
    core = core.replace('''REG_IR = m68ki_read_imm_16();
\t\t\tm68ki_instruction_jump_table[REG_IR]();
\t\t\tUSE_CYCLES(CYC_INSTRUCTION[REG_IR]);''','''{
                const daytona2_sound_entry *entry = daytona2_sound_entry_at(ADDRESS_68K(REG_PC));
                (void)m68ki_read_imm_16();
                REG_IR = entry->word;
                daytona2_m68k_current_cycles = entry->cycles;
                entry->operation();
                USE_CYCLES(entry->cycles);
            }''')
    core = core.replace('m68ki_build_opcode_table();','/* Operation selection was completed offline. */')
    core = re.sub(r'CYC_INSTRUCTION\s*= m68ki_cycles\[\d\];', 'CYC_INSTRUCTION = NULL;',core)
    core = core.replace('REG_SP = m68ki_read_imm_32();\n\tREG_PC = m68ki_read_imm_32();','REG_SP = m68k_read_immediate_32(0);\n\tREG_PC = m68k_read_immediate_32(4);')
    assert 'm68ki_instruction_jump_table' not in core
    (out/'m68kcpu.c').write_text(core)
    for name in ('m68k.h','m68kconf.h','m68kctx.h'): shutil.copyfile(MUSASHI/name,out/name)
    (out/'m68kops.h').write_text('/* Fixed-program build: no runtime opcode table. */\n')
    for old in out.glob('m68k_fixed_ops_*.c'): old.unlink()
    notice=(MUSASHI/'m68k_in.c').read_text().split('/* Input file for m68kmake')[0]
    values = list(bodies.values())
    for start in range(0,len(values),256):
        lines = [notice,'/* Generated offline; derived from the pinned Supermodel Musashi core. */\n#include "m68kcpu.h"\n']
        for name,body in values[start:start+256]: lines.append(f'void {name}(void)\n{{{body}\n}}\n')
        (out/f'm68k_fixed_ops_{start//256:03}.c').write_text(''.join(lines))
    def entry(word):
        return '{%s,0x%04x,%d,%d,%d,%d}'%(word_function[word],word,table[word][1],word>>12,1 if word&0x800 else 0,(word&255)-(256 if word&128 else 0))
    lines = [notice,'#include "m68kcpu.h"\n#include <stdio.h>\nvoid daytona2_native_fault(const char *message) __attribute__((noreturn));\nunsigned daytona2_m68k_current_cycles;\n']
    lines += [f'void {name}(void);\n' for name,_ in values]
    for board in range(2):
        lines.append(f'static const daytona2_sound_entry board_{board}[65536] = {{\n')
        lines += [entry(word)+',\n' for word in roms[board]]
        lines.append('};\n')
    lines.append('static const daytona2_sound_entry zero_padding = '+entry(0)+';\n')
    for (board,addr),word in sorted(extra_words.items()): lines.append(f'static const daytona2_sound_entry extra_{board}_{addr:06x} = '+entry(word)+';\n')
    lines.append('''void daytona2_sound_fault(unsigned pc, unsigned actual, unsigned expected) {
    char message[192];
    snprintf(message,sizeof(message),"Fixed sound program guard failed: board=%u pc=%06x actual=%04x expected=%04x",daytona2_m68k_board,pc,actual,expected);
    daytona2_native_fault(message);
}
const daytona2_sound_entry *daytona2_sound_entry_at(unsigned pc) {
    if (pc & 1) daytona2_sound_fault(pc,0,0xffffffff);
    if (daytona2_m68k_board == 0 && pc >= 0x600000 && pc < 0x700000) {
        unsigned offset = (pc-0x600000)&0x7ffff;
        return offset < 0x20000 ? &board_0[offset>>1] : &zero_padding;
    }
    if (daytona2_m68k_board == 1 && pc < 0x20000) return &board_1[pc>>1];
    switch ((daytona2_m68k_board << 24) | pc) {
''')
    for (board,addr),word in sorted(extra_words.items()): lines.append(f'case 0x{(board<<24)|addr:08x}: return &extra_{board}_{addr:06x};\n')
    lines.append('default: daytona2_sound_fault(pc,0,0xffffffff); return 0;\n}\n}\n')
    (out/'m68k_fixed_table.c').write_text(''.join(lines))
    return {'roms':identities,'aligned_rom_entries':131072,'ram_word_entries':len(extra_words),'specialized_operation_bodies':len(bodies),'runtime_opcode_decoder':False,'fallback':False}


def build_dsp(output, observations):
    source=(SOURCE/'Src/Sound/SCSPDSP.cpp').read_text()
    original=source[source.index('void SCSPDSP_Step('):source.index('void SCSPDSP_SetSample(')]
    programs = sorted({tuple(item['words']) for item in observations if item['kind']=='scspdsp'})
    # The unprogrammed SCSP is a valid zero-length program, encountered on reset.
    programs = [tuple([0]*512)] + [p for p in programs if any(p)]
    start=original.index('\tfor (step = 0;')
    dec_start=original.index('\t\tUINT16 *IPtr')
    operations=original[original.index('\t\tINT64 v;',dec_start):original.rindex('\n\t}\n\t--DSP->DEC;')]
    prelude=original[original.index('{')+1:start].replace('\tint step;','')
    declarations=re.findall(r'UINT32 (\w+) = \(IPtr\[(\d)\] >> (\d+)\) & (0x[0-9A-Fa-f]+);',original)
    assert len(declarations)==25,len(declarations)
    blocks=[]
    runners=[]
    for index,program in enumerate(programs):
        assert len(program)==512
        last=max((i//4+1 for i,w in enumerate(program) if w),default=0)
        blocks.append(f'static const UINT16 fixed_dsp_program_{index}[512] = {{'+','.join(hex(w) for w in program)+'};\n')
        blocks.append(f'static void fixed_dsp_run_{index}(_SCSPDSP *DSP)\n{{'+prelude)
        for step in range(last):
            body=operations
            fields={name:(program[4*step+int(word)]>>int(shift))&int(mask,16) for name,word,shift,mask in declarations}
            fields['step']=step
            for name,value in fields.items(): body=re.sub(r'(?<!->)\b'+name+r'\b',str(value),body)
            blocks.append(f'\n\tif (DSP->LastStep <= {step}) goto fixed_dsp_done_{index};\n\t{{\n'+body+'\n\t}\n')
        blocks.append(f'\nfixed_dsp_done_{index}:\n\t--DSP->DEC;\n\tmemset(DSP->MIXS, 0, 4 * 16);\n}}\n')
        runners.append(f'{{fixed_dsp_program_{index},fixed_dsp_run_{index}}}')
    replacement='\n'.join(blocks)+'''\nstruct FixedDSPProgram {
    const UINT16 *words;
    void (*run)(_SCSPDSP *);
};
static const FixedDSPProgram fixed_dsp_programs[] = {\n'''+',\n'.join(runners)+'''
};
void SCSPDSP_Step(_SCSPDSP *DSP) {
    if (DSP->Stopped) return;
    // The original executes no instructions while a new DSP is being uploaded.
    // MPRO may change on every sound CPU bus write during this idle state.
    if (DSP->LastStep == 0) {
        memset(DSP->EFREG,0,sizeof(DSP->EFREG));
        --DSP->DEC; memset(DSP->MIXS,0,sizeof(DSP->MIXS)); return;
    }
    if (DSP->LastStep < 0 || DSP->LastStep > 128)
        daytona2_native_fault("Invalid SCSP DSP execution limit");
    // Cache only exact, already-compiled full-image identities. Every sample
    // still compares all 1,024 bytes, including after loading a saved state.
    struct Cache { _SCSPDSP *dsp; const FixedDSPProgram *program; };
    static Cache cached[2] = {};
    unsigned slot = cached[0].dsp==DSP ? 0 : cached[1].dsp==DSP ? 1 : !cached[0].dsp ? 0 : 1;
    if (cached[slot].dsp==DSP && !memcmp(DSP->MPRO,cached[slot].program->words,sizeof(DSP->MPRO))) {
        cached[slot].program->run(DSP); return;
    }
    for (const auto &program:fixed_dsp_programs) {
        if (!memcmp(DSP->MPRO,program.words,sizeof(DSP->MPRO))) {
            cached[slot] = {DSP,&program}; program.run(DSP); return;
        }
    }
    char message[192];
    snprintf(message,sizeof(message),"Untranslated SCSP DSP program: LastStep=%d words=%04x/%04x/%04x/%04x",DSP->LastStep,DSP->MPRO[0],DSP->MPRO[1],DSP->MPRO[2],DSP->MPRO[3]);
    daytona2_native_fault(message);
}

'''
    source=source.replace(original,replacement)
    source=source.replace('#include "SCSPDSP.h"','#include "SCSPDSP.h"\n#include <cstdio>\nextern "C" void daytona2_native_fault(const char *message) __attribute__((noreturn));\n#if defined(__clang__)\n#pragma clang diagnostic ignored "-Wconstant-logical-operand"\n#endif')
    (output/'SCSPDSP.cpp').write_text(source)
    return {'fixed_programs':len(programs),'program_sha256':[sha(b''.join(w.to_bytes(2,'little') for w in p)) for p in programs], 'runtime_instruction_decoder':False,'fallback':False,'original_execution_limit_preserved':True,'zero_length_uploads_execute_no_instructions':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/generated/sound')
    parser.add_argument('--rom-dir',type=Path,default=ROOT/'Daytona USA 2 ROMs/daytona2')
    parser.add_argument('--observations',type=Path,default=ROOT/'build/reference/sound-observations.jsonl')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    observed=captures(args.observations)
    report={'schema':1,'m68k':build_musashi(args.output,args.rom_dir,observed),'scspdsp':build_dsp(args.output,observed),'observations_sha256':sha(args.observations) if args.observations.exists() else None}
    report['inputs']={str(p.relative_to(SOURCE)):sha(p) for p in list(MUSASHI.glob('*.*'))+[SOURCE/'Src/Sound/SCSPDSP.cpp']}
    report['outputs']={str(p.relative_to(args.output)):sha(p) for p in sorted(args.output.rglob('*')) if p.suffix in ('.c','.cpp','.h') and 'musashi-original' not in str(p)}
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    summary={k:dict(report[k]) for k in ('m68k','scspdsp')}
    summary['scspdsp'].pop('program_sha256')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
