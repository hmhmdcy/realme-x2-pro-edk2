"""Read exact #502 depfiles/archive/config; no helper/mount/test/build/link.

The root requested a dependency scope, not another module or source matrix.
Cached module import receipts are filtered, never rescanned from ELF here.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
BASE = Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')
B = BASE/'build'
S = BASE/'source354'
PREV = HERE.parent/'dwc-device-start-recovery-candidate'
EXPECTED = ['core','trace','gadget','ep0','debugfs','dwc3-qcom','dwc3-qcom-legacy','dwc3-generic-plat']


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):
            h.update(data)
    return h.hexdigest()


def output(argv):
    return subprocess.check_output(argv,text=True)


def main():
    assert sha(PREV/'delivery.json') == '1f3aa44fa29c8f901c39a378ff4a7d546c447c40072e3e5283226857cfcb1349'
    build_receipt=REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate/build-result.json'
    assert sha(build_receipt)=='feb6fd2e8ef8ca380f48a6f8f88b131646a874fa1d8660c3bde83a38ec8940e6'
    assert json.loads(build_receipt.read_text())['passed']
    assert sha(B/'.config')=='23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
    assert sha(B/'arch/arm64/boot/Image')=='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'
    cmdpaths=list(B.rglob('*.cmd'))
    deps=[]
    for p in cmdpaths:
        raw=p.read_bytes()
        if b'drivers/usb/dwc3/core.h' not in raw:
            continue
        first=raw.decode().splitlines()[0]
        target=first.split(' := ',1)[0].removeprefix('savedcmd_')
        assert target.startswith('drivers/usb/dwc3/') and target.endswith('.o'),target
        name=Path(target).stem
        assert name in EXPECTED,name
        deps.append(dict(target=target,cmd_path=str(p.relative_to(B)),cmd_sha256=sha(p),
                         object_sha256=sha(B/target),source_path='drivers/usb/dwc3/'+name+'.c',
                         source_sha256=sha(S/'drivers/usb/dwc3'/(name+'.c')),
                         saved_compile_command=first.split(' := ',1)[1],
                         compiled_as_module='-DMODULE' in first))
    assert {Path(r['target']).stem for r in deps}==set(EXPECTED)
    assert not any(r['compiled_as_module'] for r in deps)
    deps.sort(key=lambda r:EXPECTED.index(Path(r['target']).stem))
    archive=B/'drivers/usb/dwc3/built-in.a'
    members=[Path(l).name for l in output(['aarch64-linux-gnu-ar','t',str(archive)]).splitlines()]
    assert members==['core.o','trace.o','gadget.o','ep0.o','debugfs.o','dwc3-of-simple.o',
                     'dwc3-qcom.o','dwc3-qcom-legacy.o','dwc3-generic-plat.o']
    local_modules=(B/'drivers/usb/dwc3/modules.order').read_text().splitlines()
    global_dwc_modules=[l for l in (B/'modules.order').read_text().splitlines() if 'drivers/usb/dwc3/' in l]
    assert not local_modules and not global_dwc_modules
    config=(B/'.config').read_text().splitlines()
    config_scope=[l for l in config if l.startswith(('CONFIG_USB_DWC3','CONFIG_MODVERSIONS','CONFIG_DEBUG_INFO'))
                  or l in ['# CONFIG_USB_DWC3_HOST is not set','# CONFIG_USB_DWC3_DUAL_ROLE is not set',
                           '# CONFIG_MODVERSIONS is not set']]
    exports=[l.split() for l in (B/'vmlinux.symvers').read_text().splitlines()
             if len(l.split())>=4 and l.split()[1].startswith('dwc3_')]
    names={r[1] for r in exports}
    old_cache=Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01/original-module-imports.json')
    assert sha(old_cache)=='4f4e9536c366d60b1a7e11247ad0e122b639606bc3dd50366fb40f687514162b'
    cache=json.loads(old_cache.read_text())
    module_consumers={n:sorted(set(r['imports_from_unchanged_builtins'])&names)
                      for n,r in cache.items() if set(r['imports_from_unchanged_builtins'])&names}
    abi_payload=REF/'charging-oem-audit-20261023/gauge-image363-integration-plan/abi-payload.json'
    current=json.loads(abi_payload.read_text())
    current_consumers={n:sorted(set(imports)&names) for n,imports in current['module_imports'].items()
                       if set(imports)&names}
    # Read old/new already-built objects only. Reduced DWARF is not a layout proof.
    dwarf=[]
    for p in [B/'drivers/usb/dwc3/gadget.o',
              Path('/home/cy122/charging-management-20261023/dwc-device-start-recovery-object-01/build/drivers/usb/dwc3/gadget.o')]:
        text=output(['aarch64-linux-gnu-readelf','--debug-dump=info','--wide',str(p)])
        lines=text.splitlines()
        indexes=[i for i,l in enumerate(lines) if re.search(r'DW_AT_name\s*:.*:\s*dwc3$',l)]
        assert len(indexes)==1
        snippet='\n'.join(lines[indexes[0]-1:indexes[0]+3])
        assert 'DW_AT_declaration' in snippet
        dwarf.append(dict(path=str(p),sha256=sha(p),struct_dwc3_die=snippet,
                          complete_member_layout_available=False))
    paths=[B/'.config',B/'arch/arm64/boot/Image',B/'drivers/usb/dwc3/.built-in.a.cmd',archive,
           B/'drivers/usb/dwc3/dwc3-of-simple.o',S/'drivers/usb/dwc3/Makefile',
           *[S/'drivers/usb/dwc3'/n for n in ['gadget.c','core.h','core.c']]]
    result=dict(passed=True,mode='read-only dependency scope, no build or old-suite execution',
                exact_502_root=str(BASE),config_sha256=sha(B/'.config'),
                exact_502_build_receipt_sha256=sha(build_receipt),
                cmdfiles_examined=len(cmdpaths),core_h_dependencies=deps,
                builtin_archive_members=members,local_modules_order=local_modules,
                global_dwc3_module_targets=global_dwc_modules,configuration=config_scope,
                dwc3_exports=exports,original778_cached_dwc_importers=module_consumers,
                current481_four_module_cached_dwc_importers=current_consumers,
                original_module_cache_sha256=sha(old_cache),abi_payload_sha256=sha(abi_payload),
                dwarf=dwarf,precise_member_offsets_not_claimed=True,
                input_pins={str(p):sha(p) for p in paths},
                proposed_changed_sources=['drivers/usb/dwc3/gadget.c','drivers/usb/dwc3/core.h'],
                candidate_source_pins={n:sha(PREV/n) for n in ['gadget.c','core.h']},
                required_object_targets=[r['target'] for r in deps],
                no_dwc_module_rebuild_required_by_current_depfiles=True,
                new_Image_built=False,device_access=False,SDK_access=False,Git_used=False,
                storage_helper_or_mount_invoked=False)
    (HERE/'dependency-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,cmdfiles_examined=len(cmdpaths),
                         targets=result['required_object_targets'],module_targets=global_dwc_modules,
                         original_cached_dwc_importers=module_consumers,
                         current_camera_cached_dwc_importers=current_consumers,
                         precise_offsets_available=False)))


if __name__=='__main__':
    main()
