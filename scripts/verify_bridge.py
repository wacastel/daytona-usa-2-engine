#!/usr/bin/env python3
"""Exercise the actual native bridge's lifecycle, media and input boundaries."""
from pathlib import Path
import ctypes as C, hashlib, json, os, tempfile
from import_assets import ROOT, sha, write_json
def main():
 libpath=ROOT/'build/native/libdaytona2.dylib';lib=C.CDLL(str(libpath));ptr=C.c_void_p
 definitions={'create':([C.c_char_p,C.c_char_p],ptr),'destroy':([ptr],None),'reset':([ptr],C.c_int),'step':([ptr,C.c_float,C.c_float,C.c_float,C.c_uint32],C.c_int),'frame_number':([ptr],C.c_uint64),'fault_code':([ptr],C.c_uint32),'audio_count':([ptr],C.c_int),'error':([ptr],C.c_char_p)}
 for name,(args,result) in definitions.items():f=getattr(lib,'daytona2_'+name);f.argtypes=args;f.restype=result
 checks=[]
 def check(name,value):
  if not value:raise AssertionError(name)
  checks.append(name)
 os.environ['DAYTONA2_RTC_EPOCH']='946684800'
 with tempfile.TemporaryDirectory(prefix='daytona2-boundary-') as work:
  directory=Path(work);saves=directory/'saves'
  check('null asset path rejected',not lib.daytona2_create(None,os.fsencode(saves)))
  check('absent media rejected',not lib.daytona2_create(os.fsencode(directory),os.fsencode(saves)))
  (directory/'daytona2.zip').write_bytes(b'not canonical media')
  (directory/'Games.xml').write_bytes((ROOT/'build/assets/Games.xml').read_bytes())
  check('changed media rejected',not lib.daytona2_create(os.fsencode(directory),os.fsencode(saves)))
  context=lib.daytona2_create(os.fsencode(ROOT/'build/assets'),os.fsencode(saves));check('canonical media accepted',bool(context))
  try:
   check('second context rejected',not lib.daytona2_create(os.fsencode(ROOT/'build/assets'),os.fsencode(directory/'other')))
   for name,s,a,b,buttons in [('nan steering',float('nan'),0,0,0),('infinite accelerator',0,float('inf'),0,0),('low steering',-1.01,0,0,0),('high steering',1.01,0,0,0),('low accelerator',0,-.1,0,0),('high accelerator',0,1.1,0,0),('low brake',0,0,-.1,0),('high brake',0,0,1.1,0),('conflicting gear',0,0,0,128|256),('unexposed service bit',0,0,0,1<<16),('unknown bit',0,0,0,1<<31)]:
    check(name+' rejected',lib.daytona2_step(context,s,a,b,buttons)==0)
    check(name+' does not advance',lib.daytona2_frame_number(context)==0)
   check('valid recovery step',lib.daytona2_step(context,0,0,0,64)==1)
   check('one frame',lib.daytona2_frame_number(context)==1)
   check('735 stereo frames',lib.daytona2_audio_count(context)==735)
   check('no fault',lib.daytona2_fault_code(context)==0)
   check('reset succeeds',lib.daytona2_reset(context)==1)
   check('reset frame zero',lib.daytona2_frame_number(context)==0)
  finally:lib.daytona2_destroy(context)
  check('cabinet state saved',(saves/'daytona2.nv').is_file())
  context=lib.daytona2_create(os.fsencode(ROOT/'build/assets'),os.fsencode(saves));check('recreate existing save',bool(context))
  if context:lib.daytona2_destroy(context)
 report={'passed':True,'checks':checks,'checkCount':len(checks),'librarySHA256':sha(libpath),'scriptSHA256':sha(Path(__file__)),'scope':'Real fixed-native lifecycle and boundary checks; no stub, no gameplay or physical-controller claim.'}
 write_json(ROOT/'Documentation/bridge-acceptance.json',report);print(json.dumps({'passed':True,'checks':len(checks)}))
if __name__=='__main__':main()
