#!/usr/bin/env python3
"""Compare fixed sound operations against the untouched pinned reference core."""
from __future__ import annotations
import argparse
import ctypes
import json
import random
import resource
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from compile_sound import ROOT, SOURCE, MUSASHI, ROM_NAMES, captures, sha, build_dsp
from prepare_source import REVISION

PRODUCT_FLAGS=['-O2','-arch','arm64','-mmacosx-version-min=14.0','-fexceptions',
               '-fno-strict-aliasing','-ffp-contract=off','-DSUPERMODEL_OSX']


def build(output, generated):
    output.mkdir(parents=True,exist_ok=True)
    fixture=ROOT/'Tools/ReferenceLab/sound68k_probe.c'
    reference=[MUSASHI/'m68kcpu.c']+list((generated/'musashi-original').glob('m68kop*.c'))
    native=list((generated/'musashi').glob('*.c'))
    commands=[]
    for kind,inputs,includes in [('reference',reference,[MUSASHI,generated/'musashi-original']),('native',native,[generated/'musashi'])]:
        commands.append(['cc','-dynamiclib','-std=c11','-DINLINE=static inline']+PRODUCT_FLAGS+['-Wno-unused-function','-I'+str(SOURCE/'Src/OSD/SDL')]+['-I'+str(i) for i in includes]+[str(p) for p in inputs+[fixture]]+['-o',str(output/f'{kind}.dylib')])
    sdl=subprocess.check_output(['sdl2-config','--cflags'],text=True).split()
    synthetic=output/'synthetic'; synthetic.mkdir(exist_ok=True)
    random_fields=random.Random(20260924)
    programs=[]
    for _ in range(3):
        words=[]
        for _ in range(128):
            row=[random_fields.randrange(65536) for _ in range(4)]
            row[1]=(row[1]&~0xfc0)|(random_fields.randrange(0x32)<<6)
            words+=row
        programs.append({'kind':'scspdsp','words':words})
    (synthetic/'programs.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in programs))
    build_dsp(synthetic,programs)
    for kind,dsp in [('reference',SOURCE/'Src/Sound/SCSPDSP.cpp'),('native',generated/'SCSPDSP.cpp'),('synthetic',synthetic/'SCSPDSP.cpp')]:
        commands.append(['c++','-dynamiclib','-std=c++17']+PRODUCT_FLAGS+['-I'+str(SOURCE/'Src'),'-I'+str(SOURCE/'Src/OSD/SDL'),'-I'+str(SOURCE/'Src/Sound')]+sdl+[str(dsp),str(ROOT/'Tools/ReferenceLab/sound_dsp_probe.cpp'),'-o',str(output/f'{kind}_dsp.dylib')])
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(lambda cmd:subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True),commands):
            if result.returncode: raise RuntimeError(result.stderr)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated',type=Path,default=ROOT/'build/generated/sound')
    parser.add_argument('--output',type=Path,default=ROOT/'build/verification/sound')
    parser.add_argument('--rom-dir',type=Path,default=ROOT/'Daytona USA 2 ROMs/daytona2')
    parser.add_argument('--observations',type=Path,default=ROOT/'build/reference/sound-observations.jsonl')
    parser.add_argument('--no-build',action='store_true')
    parser.add_argument('--guard-probe',choices=('opcode','extension','unknown_pc','dsp_program'))
    args=parser.parse_args()
    if args.guard_probe:
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        if args.guard_probe=='dsp_program':
            core=ctypes.CDLL(str(args.output/'native_dsp.dylib'))
            core.sound_dsp_probe.argtypes=[ctypes.POINTER(ctypes.c_uint16),ctypes.c_uint,ctypes.c_uint]
            code=(ctypes.c_uint16*512)(); code[0]=0xffff
            core.sound_dsp_probe(code,0,1)
        else:
            core=ctypes.CDLL(str(args.output/'native.dylib'))
            core.sound_probe_load.argtypes=[ctypes.c_uint,ctypes.c_void_p]
            core.sound_probe_run.argtypes=[ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64)]
            raw=bytearray((args.rom_dir/ROM_NAMES[0]).read_bytes())
            if args.guard_probe in ('opcode','extension'): raw[0x120 if args.guard_probe=='opcode' else 0x122]^=1
            core.sound_probe_load(0,ctypes.create_string_buffer(bytes(raw)))
            result=(ctypes.c_uint64*44)()
            core.sound_probe_run(0,0x500000 if args.guard_probe=='unknown_pc' else 0x600120,1,result)
        raise RuntimeError('Guard incorrectly accepted unknown or changed code')
    if not args.no_build: build(args.output,args.generated)
    cores=[ctypes.CDLL(str(args.output/f'{kind}.dylib'),mode=ctypes.RTLD_LOCAL) for kind in ('reference','native')]
    for core in cores:
        core.sound_probe_load.argtypes=[ctypes.c_uint,ctypes.c_void_p]
        core.sound_probe_run.argtypes=[ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64)]
    trial_count=0
    for board,name in enumerate(ROM_NAMES):
        raw=(args.rom_dir/name).read_bytes()
        for core in cores: core.sound_probe_load(board,ctypes.create_string_buffer(raw))
        # Every distinct bound opcode is exercised in two register/flag states.
        positions={}
        for offset in range(0,len(raw)-32,2): positions.setdefault(int.from_bytes(raw[offset:offset+2],'little'),offset)
        for opcode,offset in positions.items():
            pc=offset+(0x600000 if board==0 else 0)
            for seed in (0x12345678,0xdeadbeef):
                results=[]
                for core in cores:
                    result=(ctypes.c_uint64*44)()
                    core.sound_probe_run(board,pc,seed,result)
                    results.append(list(result))
                assert results[0]==results[1], {'board':board,'pc':hex(pc),'word':hex(opcode),'seed':hex(seed),'differing':[(i,a,b) for i,(a,b) in enumerate(zip(*results)) if a!=b]}
                trial_count+=1
    dsps=[ctypes.CDLL(str(args.output/f'{kind}_dsp.dylib'),mode=ctypes.RTLD_LOCAL) for kind in ('reference','native')]
    for core in dsps:
        core.sound_dsp_probe.argtypes=[ctypes.POINTER(ctypes.c_uint16),ctypes.c_uint,ctypes.c_uint]
        core.sound_dsp_probe.restype=ctypes.c_uint64
        core.sound_dsp_probe_limit.argtypes=[ctypes.POINTER(ctypes.c_uint16),ctypes.c_uint,ctypes.c_uint,ctypes.c_int]
        core.sound_dsp_probe_limit.restype=ctypes.c_uint64
    programs={tuple([0]*512)}|{tuple(x['words']) for x in captures(args.observations) if x['kind']=='scspdsp'}
    limit_trials=0
    for index,program in enumerate(sorted(programs)):
        code=(ctypes.c_uint16*512)(*program)
        for seed in range(16):
            results=[core.sound_dsp_probe(code,seed,13) for core in dsps]
            assert results[0]==results[1], {'dsp_program':index,'seed':seed,'results':results}
        # LastStep is a latched execution limit, not a decoder-derived property
        # of the currently visible image while an upload is in progress.
        last=max((i//4+1 for i,word in enumerate(program) if word),default=0)
        for limit in sorted({0,1,last//2,last,128}):
            results=[core.sound_dsp_probe_limit(code,0x12345678,13,limit) for core in dsps]
            assert results[0]==results[1], {'dsp_program':index,'latched_limit':limit,'results':results}
            limit_trials+=1
    synthetic=ctypes.CDLL(str(args.output/'synthetic_dsp.dylib'),mode=ctypes.RTLD_LOCAL)
    synthetic.sound_dsp_probe.argtypes=dsps[0].sound_dsp_probe.argtypes
    synthetic.sound_dsp_probe.restype=ctypes.c_uint64
    for index,item in enumerate(captures(args.output/'synthetic/programs.jsonl')):
        code=(ctypes.c_uint16*512)(*item['words'])
        for seed in range(16):
            reference=dsps[0].sound_dsp_probe(code,seed,13)
            native=synthetic.sound_dsp_probe(code,seed,13)
            assert reference==native, {'synthetic_dsp_program':index,'seed':seed}
    report={'passed':True,'m68k_instruction_trials':trial_count,'m68k_compared':['registers','flags','pc','cycles','ordered_bus_reads','ordered_bus_writes','stop_state'], 'scspdsp_programs':len(programs),'scspdsp_trials':len(programs)*16,'scspdsp_compared':['entire_dsp_state','entire_512K_word_sample_ram'],'manifest_sha256':sha(args.generated/'manifest.json')}
    report['scspdsp_synthetic_trials']=48
    report['scspdsp_latched_limit_trials']=limit_trials
    for probe in ('opcode','extension','unknown_pc','dsp_program'):
        child=subprocess.run([sys.executable,__file__,'--output',str(args.output),'--rom-dir',str(args.rom_dir),'--guard-probe',probe],capture_output=True,text=True)
        assert child.returncode<0 and ('guard failed' in child.stderr or 'Untranslated SCSP DSP program' in child.stderr), (probe,child.returncode,child.stderr)
    report['negative_guards']=['changed opcode rejected','changed extension rejected','unknown PC rejected','unknown DSP program rejected']
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    manifest=json.loads((args.generated/'manifest.json').read_text())
    acceptance={'format':1,'passed':True,'target':'arm64-apple-macosx','upstreamCommit':REVISION,
                'compiler':subprocess.check_output(['cc','--version'],text=True).strip(),
                'flags':PRODUCT_FLAGS,
                'cpus':['SCSP sound-board 68000','DSB2 MPEG-board 68000','two SCSP DSPs'],
                'generatorSHA256':sha(ROOT/'scripts/compile_sound.py'),
                'verifierSHA256':sha(Path(__file__).resolve()),
                'fixtures':{p.name:sha(p) for p in [ROOT/'Tools/ReferenceLab/sound68k_probe.c',ROOT/'Tools/ReferenceLab/sound_dsp_probe.cpp']},
                'media':manifest['m68k']['roms'],
                'originalSources':manifest['inputs'],
                'generation':{'m68k':manifest['m68k'],'scspdsp':{k:v for k,v in manifest['scspdsp'].items() if k!='program_sha256'}},
                'captureSHA256':sha(args.observations),'productTranslationManifestSHA256':sha(args.generated/'manifest.json'),
                'differential':report,
                'limitations':['68000 comparison covers every distinct opcode from both verified ROMs at a representative ROM address in two register/flag states; it does not enumerate every address or machine state.',
                               'DSP comparison covers captured complete and transient program images plus three synthetic programs; unsupported executing images fail explicitly.',
                               'A zero LastStep executes no DSP instructions during program upload. Nonzero limits select only guarded offline-specialized operations.',
                               'Full-game frame/audio replay and physical audio/controller acceptance are separate integration requirements.']}
    source_inventory=args.observations.with_name('sound-capture-sources.json')
    if source_inventory.exists(): acceptance['captureSources']=json.loads(source_inventory.read_text())
    (ROOT/'Documentation/sound-acceptance.json').write_text(json.dumps(acceptance,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
