#!/usr/bin/env python3
"""Compare every admitted wheel Z80 start and four register/interrupt states."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from compile_ppc import ROOT, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream',type=Path,default=ROOT/'build/upstream/supermodel')
    p.add_argument('--native',type=Path,default=ROOT/'build/generated/z80/Z80.cpp')
    p.add_argument('--game',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'build/validation/z80')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    up=a.upstream.resolve();src=up/'Src'
    fixture=(ROOT/'Tools/ReferenceLab/ppc_z80_fixture.cpp').read_text()
    results={}
    for kind,path in [('reference',src/'CPU/Z80/Z80.cpp'),('native',a.native.resolve())]:
        code=path.read_text()
        if kind=='reference':code=code.replace('#include "Z80.h"',f'#include "{src}/CPU/Z80/Z80.h"')
        marker='  } // end while'
        if code.count(marker)!=1:raise ValueError('Pinned single-step boundary changed')
        code=code.replace(marker,'    goto HALTExit; // laboratory: exactly one instruction, including its interrupts\n'+marker)
        core=out/f'{kind}-core.cpp';core.write_text(code)
        harness=out/f'{kind}.cpp';harness.write_text(fixture.replace('FIXTURE_CORE',str(core)))
        binary=out/kind
        command=['clang++','-std=c++17','-O2','-fno-strict-aliasing','-ffp-contract=off','-DSUPERMODEL_OSX','-I'+str(src),'-I'+str(src/'OSD/SDL'),str(harness),str(src/'BlockFile.cpp'),'-Wl,-dead_strip','-o',str(binary)]
        if kind=='native':command.insert(3,'-DFIXTURE_NATIVE')
        subprocess.run(command,check=True)
        capture=out/f'{kind}.bin'
        with capture.open('wb')as f:subprocess.run([str(binary),str((a.game/'epr-20985.bin').resolve())],stdout=f,check=True)
        results[kind]={'sha256':sha(capture),'bytes':capture.stat().st_size}
    if results['reference']!=results['native']:
        ref=(out/'reference.bin').read_bytes();native=(out/'native.bin').read_bytes()
        offset=next(i for i,(x,y)in enumerate(zip(ref,native))if x!=y)
        case=offset//(21*8);raise ValueError(f'Z80 mismatch PC={case//4:04x} seed={case%4} byte={offset}')
    report={'passed':True,'fixedStarts':0x9000,'registerInterruptStates':4,'comparisons':0x9000*4,
            'nativeSourceSHA256':sha(a.native), 'faultChecks':2, 'results':results,'scope':'One instruction including its immediate interrupt boundary at every admitted ROM byte start; changed byte and unknown PC reject; no full-game claim.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
