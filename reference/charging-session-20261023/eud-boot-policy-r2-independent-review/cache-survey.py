"""Run under WSL for read-only cache inventory. Never invokes build tools."""
from pathlib import Path
import hashlib, json, lzma, re, struct, uuid, zlib

workspace = Path('/mnt/e/RealmeX2Pro edk2')
repo = Path('/home/cy122/edk2-samurai/repo')
build = repo / 'workspace/Build/samurai/RELEASE_GCC5'
out = workspace / 'reference/charging-session-20261023/eud-boot-policy-r2-independent-review'
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-boot')
bds = build / 'AARCH64/MdeModulePkg/Universal/BdsDxe/BdsDxe'
platform = build / 'AARCH64/Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBootManagerLib'
guid = '6d33944a-ec75-4855-a54d-809c75241f6c'
ffsdir = build / ('FV/Ffs/' + guid.upper() + 'BdsDxe')
sha = lambda b: hashlib.sha256(b).hexdigest()
def record(path):
    path = Path(path)
    if not path.is_file():
        return {'path': str(path), 'exists': False}
    data = path.read_bytes()
    return {'path': str(path), 'exists': True, 'bytes': len(data), 'sha256': sha(data)}

# Reuse parser definitions only, before its audit/execution portion.
parser = workspace / 'reference/kernel104/verify-firmware.py'
definitions = parser.read_text().split('\ndt_audit=', 1)[0]
scope = {}
exec(compile(definitions, str(parser) + ':definitions-only', 'exec'), scope)
fv, sections = scope['fv'], scope['sections']
boot_path = private / 'boot-charging-usb-dt.img'
boot = boot_path.read_bytes()
assert sha(boot) == 'a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280'
assert boot[:8] == b'ANDROID!'
kernel_size, page = struct.unpack_from('<I', boot, 8)[0], struct.unpack_from('<I', boot, 36)[0]
raw = zlib.decompress(boot[page:page+kernel_size], 31)
compact = fv(raw[144:])
images = [m for m in compact.values() if m['type'] == 0xb]
assert len(images) == 1 and len(images[0]['sections']) == 1
typ, body, section = images[0]['sections'][0]
assert typ == 2 and str(uuid.UUID(bytes_le=body[:16])) == scope['lz_guid']
offset = struct.unpack_from('<H', body, 16)[0]
nested = sections(lzma.decompress(section[offset:], format=lzma.FORMAT_ALONE))
assert len(nested) == 1 and nested[0][0] == 0x17
main = nested[0][1]
module = fv(main)[guid]
efi = next(s[1] for s in module['sections'] if s[0] == 0x10)
cached_efi = (bds/'OUTPUT/BdsDxe.efi').read_bytes()
cached_ffs = (ffsdir/(guid.upper()+'.ffs')).read_bytes()
assert cached_efi == efi
assert cached_ffs[24:] == module['body']
assert (private/'firmware/fvmain-candidate-private.Fv').read_bytes() == main
libraries = [Path(p.strip()) for p in (bds/'OUTPUT/static_library_files.lst').read_text().splitlines() if p.strip()]
paths = [bds/n for n in ['GNUmakefile','DEBUG/AutoGen.c','DEBUG/AutoGen.h','DEBUG/BdsDxe.dll',
         'OUTPUT/BdsDxe.efi','OUTPUT/BdsDxe.depex','OUTPUT/BdsDxe.lib','OUTPUT/static_library_files.lst']]
paths += [platform/n for n in ['GNUmakefile','DEBUG/AutoGen.h','OUTPUT/PlatformBm.obj',
          'OUTPUT/PlatformBootManagerLib.lib','OUTPUT/cc_resp.txt','OUTPUT/object_files.lst','deps.txt']]
paths += sorted(ffsdir.glob('*'))
tools = [Path('/usr/bin')/n for n in ['aarch64-linux-gnu-gcc','aarch64-linux-gnu-gcc-ar','aarch64-linux-gnu-ld']]
tools += [repo/'Common/edk2/BaseTools/Source/C/bin'/n for n in ['GenFw','GenSec','GenFfs']]
paths += [repo/'Common/edk2/BaseTools/Scripts/GccBase.lds',repo/'Common/edk2/ArmPkg/Library/GccLto/liblto-aarch64.a',
          repo/'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c',
          repo/'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBootManagerLib.inf']
dependencies_text = (platform/'OUTPUT/PlatformBm.obj.deps').read_text().replace('\\\n', ' ')
dependencies = [Path(p) for p in dependencies_text.splitlines()[0].split(': ', 1)[1].split()]
compiler_resources = [Path('/usr/libexec/gcc-cross/aarch64-linux-gnu/15')/n for n in ['cc1','collect2','lto1']]
compiler_resources += [Path('/usr/lib/gcc-cross/aarch64-linux-gnu/15/liblto_plugin.so')]
compiler_strings = {}
for path in [platform/'OUTPUT/PlatformBm.obj', bds/'DEBUG/BdsDxe.dll']:
    compiler_strings[str(path)] = sorted(set(s.decode('ascii') for s in re.findall(rb'GCC: [\x20-\x7e]+', path.read_bytes())))
result = {
    'scope': 'read-only inventory and binary comparison; no compilation or relink',
    'a30_carrier': record(boot_path), 'parser_definitions_source': record(parser),
    'cached_Bds_EFI_matches_actual_a30_section': True,
    'cached_Bds_FFS_body_matches_actual_a30_module': True,
    'saved_main_FV_equals_a30_embedded_main_FV': True,
    'Bds_EFI_sha256': sha(efi), 'Bds_FFS_body_sha256': sha(module['body']),
    'EFI_embedded_debug_path': [s.decode('ascii') for s in re.findall(rb'[\x20-\x7e]{8,}',efi)
                                if b'/DEBUG/BdsDxe.dll' in s],
    'link_library_count': len(libraries), 'libraries': [record(p) for p in libraries],
    'inputs': [record(p) for p in paths],
    'PlatformBm_compile_dependency_current_hashes': [record(p) for p in dependencies],
    'compiler_resources': [record(p) for p in compiler_resources],
    'tools': [dict(record(p), resolved=str(p.resolve())) for p in tools],
    'compiler_strings_in_existing_outputs': compiler_strings,
    'baseline_relink_executed': False, 'R2_build_executed': False,
    'shared_written': False, 'SDK_or_device_accessed': False,
}
assert all(x['exists'] for x in result['libraries'] + result['inputs'] + result['tools']
           + result['PlatformBm_compile_dependency_current_hashes'] + result['compiler_resources'])
out.joinpath('cache-survey-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k not in ['libraries','inputs','tools',
      'PlatformBm_compile_dependency_current_hashes','compiler_resources']}, indent=2))
