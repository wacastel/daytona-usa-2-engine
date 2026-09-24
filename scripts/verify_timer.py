#!/usr/bin/env python3
"""Qualify the native race timer flag against original inputs and read-only lab evidence."""
from pathlib import Path
import argparse, concurrent.futures, ctypes as C, hashlib, json, os, subprocess, sys, tempfile
from import_assets import ROOT, sha, write_json
sys.path.insert(0,str(ROOT/'Tools/ReferenceLab'))
from replay import png

SCENARIOS={'off':6700,'on':6700,'early':2700}
STATE={'remaining':0x105010,'elapsed':0x10500c,'phases':0x105004,'caller':0x7350ec}

def api(path):
    lib=C.CDLL(str(path));ptr=C.c_void_p
    for name,args,result in [('create',[C.c_char_p,C.c_char_p],ptr),('destroy',[ptr],None),
      ('step',[ptr,C.c_float,C.c_float,C.c_float,C.c_uint32],C.c_int),('error',[ptr],C.c_char_p),
      ('pixels',[ptr],ptr),('audio',[ptr],ptr),('audio_count',[ptr],C.c_int),
      ('set_timer_frozen',[ptr,C.c_int],C.c_int),('timer_frozen',[ptr],C.c_int),
      ('reset',[ptr],C.c_int),('frame_number',[ptr],C.c_uint64)]:
        fn=getattr(lib,'daytona2_'+name);fn.argtypes=args;fn.restype=result
    if hasattr(lib,'daytona2_diagnostic_read32'):
        lib.daytona2_diagnostic_read32.argtypes=[ptr,C.c_uint32];lib.daytona2_diagnostic_read32.restype=C.c_uint32
    return lib

def capture(args):
    out=args.output;out.mkdir(parents=True,exist_ok=True);library=args.library.resolve()
    identity=sha(library);lib=api(library)
    diagnostic=hasattr(lib,'daytona2_diagnostic_read32');reference=args.reference_capture
    if reference and args.scenario!='off':raise ValueError('The unchanged reference cannot enable timer assistance')
    route=json.loads((ROOT/'Configuration/replays/beginner-auto.json').read_text())
    with tempfile.TemporaryDirectory(prefix='daytona2-timer-') as saves:
        ctx=lib.daytona2_create(os.fsencode(ROOT/'build/assets'),os.fsencode(saves))
        if not ctx:raise RuntimeError(lib.daytona2_error(None).decode())
        try:
            assert lib.daytona2_timer_frozen(ctx)==0
            assert lib.daytona2_set_timer_frozen(ctx,-1)==0 and lib.daytona2_timer_frozen(ctx)==0
            assert lib.daytona2_set_timer_frozen(ctx,2)==0 and lib.daytona2_timer_frozen(ctx)==0
            assert lib.daytona2_set_timer_frozen(None,1)==0 and lib.daytona2_timer_frozen(None)==0
            frames=SCENARIOS[args.scenario]
            with (out/'trace.jsonl').open('w') as trace:
                for frame in range(frames):
                    controls=dict(steering=0.,accelerator=0.,brake=0.,buttons=0)
                    for event in route['events']:
                        if event['start']<=frame<event['end']:controls.update({k:v for k,v in event.items() if k in controls})
                    if frame>=2700:controls=dict(steering=0.,accelerator=0.,brake=1.,buttons=0)
                    frozen=args.scenario=='early' or (args.scenario=='on' and (2700<=frame<3300 or frame>=6500))
                    assert lib.daytona2_set_timer_frozen(ctx,int(frozen))==1
                    assert lib.daytona2_timer_frozen(ctx)==int(frozen)
                    if lib.daytona2_step(ctx,controls['steering'],controls['accelerator'],controls['brake'],controls['buttons'])!=1:
                        raise RuntimeError(f'Frame {frame+1}: '+lib.daytona2_error(ctx).decode())
                    pixels=C.string_at(lib.daytona2_pixels(ctx),496*384*4)
                    count=lib.daytona2_audio_count(ctx);pcm=C.string_at(lib.daytona2_audio(ctx),count*4)
                    row={'frame':frame+1,'frozen':frozen,'rgba':hashlib.sha256(pixels).hexdigest(),
                         'pcm':hashlib.sha256(pcm).hexdigest(),'audioFrames':count}
                    if diagnostic:row['state']={key:lib.daytona2_diagnostic_read32(ctx,address) for key,address in STATE.items()}
                    trace.write(json.dumps(row)+'\n')
                    if frame+1 in (1800,2250,2700,3000,3300,3600,5700,6000,6270,6500,6700):png(out/f'frame-{frame+1:06d}.png',pixels)
            if reference:
                assert lib.daytona2_set_timer_frozen(ctx,1)==0 and lib.daytona2_timer_frozen(ctx)==0
            else:
                assert lib.daytona2_set_timer_frozen(ctx,1)==1
                assert lib.daytona2_reset(ctx)==1 and lib.daytona2_timer_frozen(ctx)==0 and lib.daytona2_frame_number(ctx)==0
                assert lib.daytona2_set_timer_frozen(ctx,1)==1 and lib.daytona2_set_timer_frozen(ctx,0)==1
            assert sha(library)==identity
            write_json(out/'capture.json',{'passed':True,'scenario':args.scenario,'frames':frames,
                'librarySHA256':identity,'traceSHA256':sha(out/'trace.jsonl'),'diagnosticReads':diagnostic,
                'referenceEnableRejected':reference,'freshStartsOff':True,'resetTurnsOff':not reference,
                'invalidValuesAndNullRejected':True})
        finally:lib.daytona2_destroy(ctx)

def build_lab(native,out):
    """Reuse exact product objects; expose only the existing read-only bridge read."""
    out.mkdir(parents=True,exist_ok=True);manifest_path=native.parent/'engine-build-manifest.json'
    manifest=json.loads(manifest_path.read_text())
    if manifest['kind']!='native' or manifest['dynamicLibrarySHA256']!=sha(native):raise ValueError('Native manifest/library identity mismatch')
    for name,digest in manifest['compiledSources'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Native compiled source changed: '+name)
    source=ROOT/'Sources/Bridge/daytona2.cpp';original=source.read_text()
    boundary='#ifdef DAYTONA2_REFERENCE\nuint32_t daytona2_diagnostic_read32(daytona2_context* c,uint32_t address){return c->model->Read32(address);}\n'
    if original.count(boundary)!=1:raise ValueError('Read-only diagnostic source boundary changed')
    replacement='const char* daytona2_timer_lab_marker(){return "DAYTONA2_TIMER_LAB_ONLY";}\nuint32_t daytona2_diagnostic_read32(daytona2_context* c,uint32_t address){return c->model->Read32(address);}\n#ifdef DAYTONA2_REFERENCE\n'
    derived=out/'daytona2.cpp';derived.write_text(original.replace(boundary,replacement))
    upstream=ROOT/'build/upstream/supermodel';generated=ROOT/'build/generated'
    include=[ROOT/'build/derived/native',ROOT/'Sources/Bridge',generated,ROOT/'Tools/ReferenceLab',ROOT/'build/derived/musashi',upstream/'Src/CPU/68K/Musashi',upstream/'Src/Pkgs']
    include+=sorted({p.parent for p in (upstream/'Src').rglob('*') if p.suffix in ['.h','.cpp']})
    flags=['-O2','-arch','arm64','-mmacosx-version-min=14.0','-fexceptions','-fno-strict-aliasing','-ffp-contract=off','-DGLEW_STATIC','-DSUPERMODEL_OSX','-Wno-deprecated-declarations','-Wno-unused-result','-Wno-register','-std=c++17']+['-I'+str(p) for p in include]
    bridge_object=out/'daytona2-lab.o'
    subprocess.run(['clang++',*flags,'-c',str(derived),'-o',str(bridge_object)],check=True)
    objects=[];identities={}
    for filename in manifest['compiledSources']:
        path=ROOT/filename
        if path==source:continue
        obj=native.parent/'objects'/(path.stem+'-'+hashlib.sha256(str(path).encode()).hexdigest()[:8]+'.o')
        objects.append(obj);identities[str(obj.relative_to(ROOT))]=sha(obj)
    library=out/'libdaytona2-timer-lab.dylib'
    subprocess.run(['clang++','-dynamiclib','-arch','arm64','-mmacosx-version-min=14.0','-Wl,-dead_strip','-o',str(library),*map(str,objects),str(bridge_object),'-framework','OpenGL','-framework','Foundation','-lz'],check=True)
    symbols=subprocess.check_output(['nm','-gU',str(library)],text=True)
    assert '_daytona2_timer_lab_marker' in symbols and '_daytona2_diagnostic_read32' in symbols
    report={'nativeLibrarySHA256':sha(native),'nativeManifestSHA256':sha(manifest_path),
        'originalBridgeSHA256':sha(source),'derivedBridgeSHA256':sha(derived),'derivedBridgeObjectSHA256':sha(bridge_object),
        'reusedProductObjects':identities,'librarySHA256':sha(library),
        'scope':'Same product objects and native compile settings; derived bridge adds a lab marker and exposes only its existing read-only RAM accessor. No reference CPU, RAM writes, layout introspection or save-state injection.'}
    write_json(out/'manifest.json',report);return library,report

def rows(path):return [json.loads(line) for line in path.read_text().splitlines()]
def picture(row):return {key:row[key] for key in ('frame','rgba','pcm','audioFrames')}
def equivalent(a,b,flag=True):
    assert len(a)==len(b)
    for x,y in zip(a,b):
        assert picture(x)==picture(y),f"Frame output differs at {x['frame']}"
        if flag:assert x['frozen']==y['frozen']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native',type=Path,default=ROOT/'build/native/libdaytona2.dylib')
    parser.add_argument('--reference',type=Path,default=ROOT/'build/reference/libdaytona2.dylib')
    parser.add_argument('--output',type=Path,default=ROOT/'build/validation/timer')
    parser.add_argument('--capture',action='store_true');parser.add_argument('--library',type=Path)
    parser.add_argument('--scenario',choices=SCENARIOS,default='off');parser.add_argument('--reference-capture',action='store_true')
    args=parser.parse_args();os.environ['DAYTONA2_RTC_EPOCH']='946684800';os.environ.pop('DAYTONA2_FACTORY_SETTINGS',None)
    if args.capture:return capture(args)
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    binding=[Path(__file__).resolve(),ROOT/'Sources/Bridge/daytona2.cpp',ROOT/'Sources/Bridge/daytona2.h',
        ROOT/'scripts/compile_ppc.py',ROOT/'build/generated/ppc/translation-manifest.json',ROOT/'build/native/engine-build-manifest.json',
        ROOT/'build/reference/engine-build-manifest.json',ROOT/'Configuration/replays/beginner-auto.json',
        ROOT/'build/assets/media-identity.json',args.native.resolve(),args.reference.resolve()]
    identities={str(path.relative_to(ROOT)):sha(path) for path in binding}
    shipping_symbols=subprocess.check_output(['nm','-gU',str(args.native)],text=True)
    assert '_daytona2_diagnostic_read32' not in shipping_symbols and '_daytona2_timer_lab_marker' not in shipping_symbols
    lab,lab_report=build_lab(args.native.resolve(),out/'lab')
    jobs=[('reference-off',args.reference,'off',True),('native-off',args.native,'off',False),
          ('native-on',args.native,'on',False),('lab-on',lab,'on',False),
          ('native-early',args.native,'early',False),('lab-early',lab,'early',False)]
    def run(job):
        name,library,scenario,reference=job;dest=out/name;dest.mkdir(exist_ok=True)
        command=[sys.executable,str(Path(__file__).resolve()),'--capture','--library',str(library.resolve()),'--scenario',scenario,'--output',str(dest)]
        if reference:command.append('--reference-capture')
        with (dest/'run.log').open('w') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        return name,rows(dest/'trace.jsonl')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:data=dict(pool.map(run,jobs))
    ref,off,on,held,early,early_state=[data[key] for key in ['reference-off','native-off','native-on','lab-on','native-early','lab-early']]
    equivalent(ref,off);equivalent(on,held);equivalent(early,early_state)
    equivalent(ref[:2700],on[:2700]);equivalent(ref[:2250],early[:2250],flag=False)
    remaining=lambda row:row['state']['remaining'];elapsed=lambda row:row['state']['elapsed']
    assert remaining(ref[2249])==3420 and remaining(ref[2250])==3419
    assert all(remaining(row)==3420 for row in early_state[2249:])
    assert elapsed(early_state[-1])==450
    value=remaining(held[2699]);assert value==2970
    assert all(remaining(row)==value for row in held[2700:3300])
    assert elapsed(held[3299])-elapsed(held[2699])==600
    assert all((row['state']['phases']>>24)==17 and ((row['state']['caller']>>8)&255)==13 for row in held[2700:3300])
    assert remaining(held[3300])==value-1 and remaining(held[3301])==value-2
    ref_zero=next(row['frame'] for row in ref if row['frame']>2700 and remaining(row)==0)
    held_zero=next(row['frame'] for row in held if row['frame']>3300 and remaining(row)==0)
    assert ref_zero==5670 and held_zero==ref_zero+600
    assert remaining(ref[ref_zero])==0xffffffff and remaining(held[held_zero])==0xffffffff
    assert all(remaining(row)==0xffffffff for row in held[6500:])
    assert sha(lab)==lab_report['librarySHA256']
    assert identities=={str(path.relative_to(ROOT)):sha(path) for path in binding},'Qualification inputs changed while running'
    assert all(sha(ROOT/path)==digest for path,digest in lab_report['reusedProductObjects'].items())
    report={'passed':True,'productNativeLibrarySHA256':sha(args.native),'originalReferenceLibrarySHA256':sha(args.reference),
      'identities':identities,'diagnosticLab':lab_report,'frames':{'referenceParity':6700,'productVsReadOnlyLabOn':6700,'productVsReadOnlyLabEarly':2700},
      'facts':{'initialCounter':3420,'firstDecrementFrame':2251,'freezeFromBootPreservesInitializationFrames':2250,
        'liveHoldFrames':600,'liveHeldCounter':2970,'elapsedGainWhileHeld':600,'resumedFirstCounter':2969,
        'originalZeroFrame':ref_zero,'heldZeroFrame':held_zero,'expiredEnableFrame':6501,'expiredEnableObservedFrames':200,
        'freshStartsOff':True,'resetTurnsOff':True,'invalidValuesAndNullRejected':True,'referenceEnableRejected':True},
      'captures':{name:json.loads((out/name/'capture.json').read_text()) for name,*_ in jobs},
      'scope':['Only original driving inputs and the public native timer flag; brake from frame2701 prevents checkpoint extensions in this controlled countdown test.',
        'Complete shipping native RGBA/PCM/count output matches the unchanged original with assistance OFF, and independently matches the product-object read-only diagnostic lab with assistance ON.',
        'Original boot/menu/pre-race output remains equal when enabled early. Positive countdown holds while original elapsed time advances; OFF resumes next decrement; enabling after expiry does not revive the race.',
        'The same-ROM checkpoint extension instructions remain untouched, but this bounded timer test does not exercise every course/extension/finish state or physical controller actuation.']}
    write_json(out/'acceptance.json',report);write_json(ROOT/'Documentation/timer-acceptance.json',report)
    print(json.dumps({'passed':True,'output':str(out.relative_to(ROOT)),'parityFrames':6700,'timerNativeLabFrames':9400}))
if __name__=='__main__':main()
