#!/usr/bin/env python3
"""Reproduce the fixed port from pinned source and locally supplied Revision A media."""
from pathlib import Path
import argparse, json, os, subprocess, sys
from import_assets import ROOT
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--game',type=Path,default=ROOT/'Daytona USA 2 ROMs/daytona2');ap.add_argument('--jobs',type=int,default=8);args=ap.parse_args()
 def run(*command,env=None):
  print('Running '+str(command[0]),flush=True)
  subprocess.run([sys.executable,str(ROOT/command[0])]+[str(x) for x in command[1:]],cwd=ROOT,env=env,check=True)
 run('scripts/prepare_source.py')
 run('scripts/import_assets.py','--game',args.game.resolve())
 run('scripts/compile_ppc.py','--observer-only')
 run('scripts/build_engine.py','--kind','observer','--jobs',args.jobs)
 run('scripts/prepare_settings.py')
 # The observer is a laboratory-only original processor build. It discovers
 # exact uploaded program identities before any shipping compilation occurs.
 capture=ROOT/'build/qualification';capture.mkdir(parents=True,exist_ok=True)
 ppc=capture/'ppc.tsv';sound=capture/'sound.jsonl'
 ppc.write_text('');sound.write_text('')
 environment={**os.environ,'DAYTONA2_PPC_TRACE':str(ppc),'DAYTONA2_SOUND_CAPTURE':str(sound),'DAYTONA2_RTC_EPOCH':'946684800'}
 environment.pop('DAYTONA2_FACTORY_SETTINGS',None)
 # Rebuild after producing the authenticated clean USA/single-cabinet seed.
 run('scripts/build_engine.py','--kind','observer','--jobs',args.jobs)
 routes=[ROOT/'Configuration/replays'/name for name in ['beginner-auto.json','beginner-manual.json','advanced-auto.json','expert-auto.json']]
 for route in routes:
  if not route.is_file():raise RuntimeError('Missing qualified gameplay route: '+route.name)
  count=json.loads(route.read_text())['frames']
  run('Tools/ReferenceLab/replay.py','--route',route,'--frames',count,'--output',capture/route.stem,'--capture-every','600',env=environment)
 helper=capture/routes[0].stem/'helper-63d000-code.bin'
 run('scripts/compile_ppc.py','--game',args.game.resolve(),'--observations',ppc,'--ram-image','0x63d000:'+str(helper))
 run('scripts/compile_sound.py','--rom-dir',args.game.resolve(),'--observations',sound)
 run('scripts/compile_z80.py','--game',args.game.resolve())
 run('scripts/verify_ppc.py','--game',args.game.resolve(),'--observations',ppc,'--ram-image','0x63d000:'+str(helper))
 run('scripts/verify_z80.py','--game',args.game.resolve())
 run('scripts/verify_sound.py','--rom-dir',args.game.resolve(),'--observations',sound)
 run('scripts/build_engine.py','--kind','native','--jobs',args.jobs)
 run('scripts/build_engine.py','--kind','reference','--jobs',args.jobs)
 run('scripts/verify_integration.py','--routes',*routes)
 run('scripts/verify_bridge.py')
 run('scripts/prepare_licenses.py')
 print('Fixed-native engine and original-reference gameplay comparisons completed. Run scripts/build.sh --skip-engine to package.')
if __name__=='__main__':main()
