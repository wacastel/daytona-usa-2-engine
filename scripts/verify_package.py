#!/usr/bin/env python3
"""Audit the actual native macOS app and engine; gameplay acceptance is separate."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
from prepare_source import ROOT, sha, write_json

FORBIDDEN = ('daytona2_reference_probe_marker', 'daytona2_diagnostic_engine_marker',
             'daytona2_test_stub_marker', 'daytona2_diagnostic_', 'daytona2_sound_observe',
             'daytona2_ppc_observe', 'm68ki_instruction_jump_table', 'm68ki_build_opcode_table',
             'm68k_op_', 'm68k_disassemble', 'PPCDisasm', 'optable19', 'optable31',
             'optable59', 'optable63', 'SDL_')
FIXED_SYMBOLS = ('daytona2_ppc_program', 'daytona2_ppc_operations',
                 'daytona2_ppc_race_countdown', 'daytona2_set_timer_frozen', 'daytona2_timer_frozen',
                 'daytona2_sound_entry_at', 'daytona2_sound_op_',
                 'fixed_dsp_program_', 'daytona2_z80_program')


def verify_engine_sources(engine):
    if not engine.get('sources') or not engine.get('generatedSources') or not engine.get('compiledSources') or set(engine.get('cpuReplacements', {})) != {'PowerPC', 'Musashi-SCSP', 'Z80'}:
        raise RuntimeError('Engine must bind source identities and PPC, Z80 and sound replacement manifests')
    for name, digest in {**engine['sources'], **engine['generatedSources'], **engine['compiledSources']}.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or sha(ROOT / relative) != digest:
            raise RuntimeError('Engine source identity changed: ' + name)
    upstream = ROOT / 'build/upstream/supermodel'
    if not (ROOT / 'build/generated/settings_identity.h').is_file():
        raise RuntimeError('The native product requires authenticated first-launch cabinet settings')
    headers = sorted(set((upstream / 'Src').rglob('*.h')) |
                     set((ROOT / 'Sources/Bridge').glob('*.h')) |
                     set((ROOT / 'build/generated').rglob('*.h')) |
                     set((ROOT / 'build/derived/native').glob('*.h')) |
                     set((ROOT / 'build/derived/musashi').glob('*.h')))
    digest = hashlib.sha256(''.join(str(p.relative_to(ROOT)) + sha(p) for p in headers).encode()).hexdigest()
    if digest != engine.get('headersSHA256'):
        raise RuntimeError('Engine header identities changed; rebuild before packaging')
    replacement_hashes = {}
    for cpu, entry in engine['cpuReplacements'].items():
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts or sha(ROOT / relative) != entry['sha256']:
            raise RuntimeError('CPU manifest changed: ' + cpu)
        if cpu == 'PowerPC' and json.loads((ROOT / relative).read_text()).get('timerFreeze', {}).get('implemented') is not True:
            raise RuntimeError('The native product requires the authenticated race-countdown hook')
        replacement_hashes[cpu] = entry['sha256']
    return replacement_hashes


def command(arguments):
    result = subprocess.run([str(x) for x in arguments], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Inspection failed: ' + str(arguments[0]) + '\n' + result.stderr)
    return result.stdout + result.stderr


def binary_audit(path: Path, *, library=False):
    architecture = command(['/usr/bin/lipo', '-archs', path]).strip()
    if architecture != 'arm64': raise RuntimeError('Expected only arm64: ' + path.name)
    symbols = command(['/usr/bin/nm', path])
    bad = [word for word in FORBIDDEN if word in symbols]
    if re.search(r'\b_[A-Za-z0-9_]*optable\b', symbols): bad.append('original optable')
    if bad: raise RuntimeError('Forbidden linked symbols in ' + path.name + ': ' + ', '.join(bad))
    missing = [word for word in FIXED_SYMBOLS if word not in symbols]
    if missing: raise RuntimeError('Fixed execution symbols missing from ' + path.name + ': ' + ', '.join(missing))
    for name in ['create', 'destroy', 'step', 'pixels', 'audio', 'audio_count']:
        if '_daytona2_' + name not in symbols: raise RuntimeError('Missing host C ABI symbol: ' + name)
    dependencies = [line.strip().split(' (', 1)[0] for line in command(['/usr/bin/otool', '-L', path]).splitlines()[1:] if line.strip()]
    if library: dependencies = dependencies[1:]  # LC_ID_DYLIB is the library's own identity.
    if any(not p.startswith(('/System/Library/', '/usr/lib/')) for p in dependencies):
        raise RuntimeError('Non-system runtime dependency: ' + json.dumps(dependencies))
    loads = command(['/usr/bin/otool', '-l', path])
    versions = re.findall(r'cmd LC_BUILD_VERSION\s+cmdsize \d+\s+platform 1\s+minos ([\d.]+)', loads)
    if versions != ['14.0']: raise RuntimeError('Expected macOS 14.0 deployment load command: ' + path.name)
    return {'sha256': sha(path), 'architecture': architecture, 'minimumMacOS': '14.0',
            'dependencies': dependencies, 'fixedSymbolFamiliesPresent': list(FIXED_SYMBOLS),
            'forbiddenSymbolMatches': [], 'symbolInventorySHA256': hashlib.sha256(symbols.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, default=ROOT / 'build/Daytona USA 2.app')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/verification/package-acceptance.json')
    args = parser.parse_args()
    app = args.app.resolve(); executable = app / 'Contents/MacOS/DaytonaUSA2'
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    if info['CFBundleIdentifier'] != 'local.william.daytonausa2' or info['CFBundleExecutable'] != 'DaytonaUSA2':
        raise RuntimeError('Incorrect application identity')
    command(['/usr/bin/codesign', '--verify', '--strict', app])
    signature = command(['/usr/bin/codesign', '-d', '--verbose=4', app])
    if 'Signature=adhoc' not in signature: raise RuntimeError('Expected locally ad hoc signed product')
    engine_path = ROOT / 'build/native/engine-build-manifest.json'
    engine = json.loads(engine_path.read_text())
    if engine.get('kind') != 'native' or engine.get('shippingNative') is not True or engine.get('diagnostics') is not False:
        raise RuntimeError('Engine manifest does not identify a shipping native engine')
    if sha(ROOT / 'build/native/libdaytona2.a') != engine['staticArchiveSHA256']:
        raise RuntimeError('Engine archive hash changed')
    if sha(ROOT / 'build/native/libdaytona2.dylib') != engine['dynamicLibrarySHA256']:
        raise RuntimeError('Engine library hash changed')
    replacement_hashes = verify_engine_sources(engine)
    package = json.loads((ROOT / 'build/package-manifest.json').read_text())
    if package['executableSHA256'] != sha(executable) or package['engineManifestSHA256'] != sha(engine_path):
        raise RuntimeError('Packaged executable or engine identity changed')
    if package['nativeArchiveSHA256'] != engine['staticArchiveSHA256']:
        raise RuntimeError('Packaged engine archive identity differs')
    host_sources = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'Sources/Mac').glob('*.swift')}
    packaging_sources = {'scripts/build.sh', 'scripts/build_host.sh', 'scripts/build_icon.sh',
                         'scripts/build_icon.swift', 'scripts/verify_package.py', 'Resources/Info.plist'}
    if set(package.get('hostSources', {})) != host_sources or set(package.get('packagingSources', {})) != packaging_sources:
        raise RuntimeError('Packaged host and packaging source inventories must match exactly')
    for name, digest in {**package['hostSources'], **package['packagingSources']}.items():
        if sha(ROOT / name) != digest: raise RuntimeError('Packaged host source changed: ' + name)
    if sha(app / 'Contents/Info.plist') != package['packagingSources']['Resources/Info.plist']:
        raise RuntimeError('Bundled app metadata differs from packaging source')
    media_path = app / 'Contents/Resources/Media/media-identity.json'
    media = json.loads(media_path.read_text())
    if sha(media_path) != package['mediaManifestSHA256'] or sha(media_path) != sha(ROOT / 'build/assets/media-identity.json'):
        raise RuntimeError('Bundled media manifest changed')
    names = {row['path'] for row in media['files']}
    if len(names) != len(media['files']) or names != {'daytona2.zip', 'Games.xml', 'default.nv'}:
        raise RuntimeError('Unexpected media inventory')
    for row in media['files']:
        path = media_path.parent / row['path']
        if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise RuntimeError('Bundled media changed: ' + row['path'])
    licenses = [p for p in (ROOT / 'Licenses').rglob('*') if p.is_file()]
    bundled_licenses = app / 'Contents/Resources/Licenses'
    for path in licenses:
        if sha(bundled_licenses / path.relative_to(ROOT / 'Licenses')) != sha(path):
            raise RuntimeError('Bundled source notice differs: ' + path.name)
    icon = app / 'Contents/Resources/AppIcon.icns'
    if sha(icon) != package['iconSHA256'] or not icon.read_bytes().startswith(b'icns'):
        raise RuntimeError('Application icon changed or is not an ICNS file')
    report = {'passed': True, 'appIdentity': info['CFBundleIdentifier'],
              'executable': binary_audit(executable),
              'nativeLibrary': binary_audit(ROOT / 'build/native/libdaytona2.dylib', library=True),
              'adHocSignatureVerified': True, 'mediaFilesVerified': len(media['files']),
              'licenseFilesVerified': len(licenses), 'iconSHA256': sha(icon),
              'engineManifestSHA256': sha(engine_path), 'cpuReplacementManifests': replacement_hashes,
              'hostSourceFilesVerified': len(host_sources),
              'packagingSourceFilesVerified': len(packaging_sources),
              'packageManifestSHA256': sha(ROOT / 'build/package-manifest.json'),
              'scriptSHA256': sha(Path(__file__)),
              'scope': 'Actual packaged artifact and library architecture, dependencies, known decoder/diagnostic symbol boundaries, fixed execution symbol families, build provenance, signature and resources. A symbol audit is not a proof of all execution semantics; CPU fixtures, original-reference replay and live-host observations are separate.'}
    write_json(args.output, report)
    print(json.dumps({'passed': True, 'output': str(args.output.relative_to(ROOT)),
                      'executableSHA256': report['executable']['sha256']}))


if __name__ == '__main__': main()
