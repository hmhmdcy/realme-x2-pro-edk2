"""One private gadget.o from the exact #502 saved W=1 command. No make/link.

All changed C/header/output and copied generated includes are private. Original
284 helper is used only to establish the fixed source/build storage identity.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
BASE = Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')
OUT = Path('/home/cy122/charging-management-20261023/dwc-device-start-recovery-object-01')


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for data in iter(lambda: stream.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()


def main():
    tests = json.loads((HERE/'test-result.json').read_text())
    assert tests['passed'] and tests['summary']['cases'] == 20
    for name, digest in tests['files'].items():
        assert sha(HERE/name) == digest, name
    source = json.loads((HERE/'source-result.json').read_text())
    for name, digest in source['original'].items():
        assert sha(BASE/'source354/drivers/usb/dwc3'/name) == digest, name
    assert sha(BASE/'build/.config') == '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
    assert not OUT.exists(), 'unique output; no replay'
    helper = REF/'kernel284/storage.py'
    assert sha(helper) == '5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
    spec = importlib.util.spec_from_file_location('storage284_dwc_start_object', helper)
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    shared = storage.mounted_build()
    original = shared.parent/'source354'
    cmdpath = BASE/'build/drivers/usb/dwc3/.gadget.o.cmd'
    assert sha(cmdpath) == '91798b26a98f25c67b6694b24a59f401d4436a3704f1f1388a30a306f3f949d2'
    tracked = [helper, cmdpath, BASE/'build/.config', BASE/'build/Module.symvers',
               BASE/'build/vmlinux', BASE/'build/arch/arm64/boot/Image',
               BASE/'build/drivers/usb/dwc3/gadget.o',
               *[BASE/'source354/drivers/usb/dwc3'/n for n in ['gadget.c','core.h','core.c','Makefile']],
               *[shared/n for n in ['.config','Module.symvers','arch/arm64/boot/Image','drivers/usb/dwc3/gadget.o']],
               *[original/'drivers/usb/dwc3'/n for n in ['gadget.c','core.h','core.c','Makefile']]]
    before = {str(p):sha(p) for p in tracked}
    mount_before = Path('/proc/self/mountinfo').read_bytes()
    OUT.mkdir(parents=True)
    view = OUT/'source-view'
    build = OUT/'build'

    def branch(src, dst, selected):
        dst.mkdir()
        for p in src.iterdir():
            if p.name == '.git':
                continue
            q = dst/p.name
            if p.name in selected:
                branch(p, q, selected[p.name])
            else:
                q.symlink_to(p, target_is_directory=p.is_dir())

    branch(BASE/'source354', view, {'drivers':{'usb':{'dwc3':{}}}})
    for name in ['gadget.c','core.h']:
        p = view/'drivers/usb/dwc3'/name
        p.unlink()  # Only the newly created private symlink.
        shutil.copy2(HERE/name,p)
        assert not p.is_symlink() and p.stat().st_nlink == 1
    (build/'drivers/usb/dwc3').mkdir(parents=True)
    for name in ['include','arch/arm64/include/generated']:
        shutil.copytree(BASE/'build'/name,build/name)
    shutil.copy2(BASE/'build/.config',build/'.config')
    raw = cmdpath.read_text().splitlines()[0].split(':=',1)[1].strip()
    assert raw.count('/mnt/samurai-full282/source354/drivers/usb/dwc3/gadget.c') == 1
    assert '-DKBUILD_EXTRA_WARN1' in raw and '-Wextra' in raw
    raw = raw.replace('/mnt/samurai-full282/source354',str(view))
    argv = shlex.split(raw)
    assert argv[0] == 'aarch64-linux-gnu-gcc'
    assert argv[-1] == str(view/'drivers/usb/dwc3/gadget.c')
    assert argv[argv.index('-o')+1] == 'drivers/usb/dwc3/gadget.o'
    argv.insert(1,'-Werror')
    (OUT/'actual-command.json').write_text(json.dumps(argv,indent=2)+'\n')
    started = time.monotonic()
    with (OUT/'stdout.log').open('w') as stdout, (OUT/'stderr.log').open('w') as stderr:
        proc = subprocess.Popen(argv,cwd=build,stdout=stdout,stderr=stderr)
        print(json.dumps(dict(phase='compile',pid=proc.pid,private_output=str(OUT))),flush=True)
        rc = proc.wait()
    after = {str(p):sha(p) for p in tracked}
    diagnostics = [s for s in (OUT/'stderr.log').read_text().splitlines()
                   if re.search(r'warning:|error:',s,re.I)]
    obj = build/'drivers/usb/dwc3/gadget.o'
    source_pins = {n:sha(view/'drivers/usb/dwc3'/n) for n in ['gadget.c','core.h','core.c']}
    assert source_pins['core.c'] == source['original']['core.c']
    mount_after = Path('/proc/self/mountinfo').read_bytes()
    passed = rc == 0 and not diagnostics and before == after and mount_before == mount_after
    result = dict(passed=passed,phase=dict(pid=proc.pid,terminal=True,returncode=rc,
                  seconds=time.monotonic()-started),
                  private_output=str(OUT),object_path=str(obj),object_sha256=sha(obj) if obj.exists() else None,
                  object_size=obj.stat().st_size if obj.exists() else None,
                  command=argv,command_json_sha256=sha(OUT/'actual-command.json'),
                  saved_command_source=str(cmdpath),saved_command_sha256=sha(cmdpath),
                  compiler_version=subprocess.check_output([argv[0],'-dumpfullversion','-dumpversion'],text=True).strip(),
                  diagnostic_lines=diagnostics,stdout_sha256=sha(OUT/'stdout.log'),stderr_sha256=sha(OUT/'stderr.log'),
                  sources=source_pins,files={n:sha(HERE/n) for n in ['build-object.py','test-result.json','gadget.c','core.h']},
                  inputs_before=before,inputs_after=after,tracked_inputs_unchanged=before==after,
                  parent_mounts_unchanged=mount_before==mount_after,
                  parent_mountinfo_sha256=hashlib.sha256(mount_after).hexdigest(),
                  no_make=True,no_link=True,no_Image=True,no_ko=True,no_SDK=True,no_device=True)
    (HERE/'build-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','phase','object_sha256','object_size',
                                         'diagnostic_lines','tracked_inputs_unchanged','parent_mounts_unchanged']}),flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
