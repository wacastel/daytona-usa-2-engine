#!/usr/bin/env python3
"""Create first-launch cabinet settings through the original game's Test Menu.

The reference engine receives ordinary button inputs into a fresh save directory.
No ROM, EEPROM, backup RAM, or supplied save is patched. Only the resulting
validated local save is copied into ignored build/assets/default.nv.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT/'Configuration/replays/cabinet-setup.json'
# Identical in independent original-menu runs (interactive and bounded replay).
EEPROM_SHA256 = '7e4c41b6d4b63efb5b505250151f6cf3b8c59111c74efed94fd36f321cdcdb37'


def sha(data):
    if isinstance(data, Path): data=data.read_bytes()
    return hashlib.sha256(data).hexdigest()


def blocks(data):
    """Read the pinned Supermodel CBlockFile format without changing bytes."""
    result={};position=0
    while position<len(data):
        assert len(data)-position>=12, 'Truncated NVRAM block header'
        size,namesize,commentsize=struct.unpack_from('<III',data,position)
        assert namesize and commentsize and size>=12+namesize+commentsize
        assert position+size<=len(data)
        name=data[position+12:position+12+namesize]
        assert name[-1]==0 and name[:-1].decode() not in result
        start=position+12+namesize+commentsize
        result[name[:-1].decode()]=(start,data[start:position+size])
        position+=size
    return result


def validate(data):
    parsed=blocks(data)
    assert '93C46' in parsed and 'Backup RAM' in parsed
    base,payload=parsed['93C46']
    assert len(payload)>=128 and len(parsed['Backup RAM'][1])==0x20000
    eeprom=payload[:128]
    words=struct.unpack('<64H',eeprom)
    assert words[:3]==(0x4d33,0x5345,0x4741), 'Missing original M3SEGA EEPROM signature'
    # Country-only and link-only changes were isolated by independent menu runs.
    expected={0x03:0x32ca,0x06:2,0x0c:0x0200,0x0f:0,0x23:2,0x29:0x0200,0x2c:0}
    for word,value in expected.items():
        assert words[word]==value, f'Unexpected cabinet EEPROM word {word:02x}: {words[word]:04x}'
    assert sha(eeprom)==EEPROM_SHA256, 'Original USA/SINGLE settings or checksum differ'
    return {'country':'USA','linkID':'SINGLE','eepromPayloadOffset':base,
            'eepromSHA256':sha(eeprom),'storedChecksumWord':'0x32ca',
            'verifiedWords':{f'0x{k:02x}':f'0x{v:04x}' for k,v in expected.items()},
            'backupRAMBytes':len(parsed['Backup RAM'][1])}


def image_colors(path):
    """Inspect the simple RGBA PNGs written by the reference replay fixture."""
    data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
    compressed=bytearray();position=8
    while position<len(data):
        size=struct.unpack_from('>I',data,position)[0]
        kind=data[position+4:position+8]
        if kind==b'IDAT': compressed.extend(data[position+8:position+8+size])
        position+=size+12
    raw=zlib.decompress(compressed);stride=496*4+1
    assert len(raw)==384*stride and all(raw[y*stride]==0 for y in range(384))
    return len({raw[y*stride+1+x*4:y*stride+5+x*4] for y in range(384) for x in range(496)})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,default=ROOT/'build/observer/libdaytona2.dylib')
    args=parser.parse_args()
    library=args.library.resolve()
    reference=ctypes.CDLL(str(library))
    assert hasattr(reference,'daytona2_reference_probe_marker'), 'Cabinet setup requires the isolated reference engine'
    route=json.loads(ROUTE.read_text());frames=route['frames']
    assert frames==2485 and all(0<=e['start']<e['end']<=frames for e in route['events'])
    settings=ROOT/'build/settings';settings.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='prepare-',dir=settings))
    fresh=work/'factory-save'
    environment=os.environ.copy()
    environment.update(DAYTONA2_FACTORY_SETTINGS='1',DAYTONA2_RTC_EPOCH='946684800',
                       DAYTONA2_SOUND_CAPTURE=str(work/'sound.jsonl'),DAYTONA2_PPC_TRACE=str(work/'ppc.tsv'))
    command=[sys.executable,str(ROOT/'Tools/ReferenceLab/replay.py'),'--library',str(library),
             '--route',str(ROUTE),'--frames',str(frames),'--capture-every','100',
             '--output',str(work/'replay'),'--saves',str(fresh)]
    print(f'Replaying {frames} original Test Menu frames into fresh local settings.',flush=True)
    with (work/'replay.log').open('w') as log:
        subprocess.run(command,cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True)
    raw=(fresh/'daytona2.nv').read_bytes()
    evidence=validate(raw)
    replay=json.loads((work/'replay/report.json').read_text())
    assert replay['passed'] and replay['frames']==frames and replay['nonzeroPCMBytes']>0
    final_image=work/f'replay/frame-{frames:06d}.png'
    colors=image_colors(final_image)
    assert colors>256, 'Final replay frame did not render the original game attract scene'
    assets=ROOT/'build/assets';assets.mkdir(parents=True,exist_ok=True)
    pending=assets/'default.nv.tmp';pending.write_bytes(raw);pending.replace(assets/'default.nv')
    identity_path=assets/'media-identity.json'
    identity=json.loads(identity_path.read_text())
    identity['files']=[item for item in identity['files'] if item['path']!='default.nv']
    identity['files'].append({'path':'default.nv','bytes':len(raw),'sha256':sha(raw)})
    identity_path.write_text(json.dumps(identity,indent=2)+'\n')
    generated=ROOT/'build/generated';generated.mkdir(parents=True,exist_ok=True)
    (generated/'settings_identity.h').write_text('#pragma once\n// Generated from original game menu inputs; local media only.\nconstexpr const char *daytona2_settings_sha256 = "'+sha(raw)+'";\n')
    report={'passed':True,**evidence,'seedSHA256':sha(raw),'seedBytes':len(raw),
            'referenceSHA256':sha(library),'routeSHA256':sha(ROUTE),'frames':frames,
            'factoryOverride':'DAYTONA2_FACTORY_SETTINGS=1','clockEpoch':946684800,
            'finalFrameColors':colors,'finalFrame':str(final_image.relative_to(ROOT)),
            'nonzeroPCMBytes':replay['nonzeroPCMBytes'],'evidenceDirectory':str(work.relative_to(ROOT))}
    (settings/'prepared.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
