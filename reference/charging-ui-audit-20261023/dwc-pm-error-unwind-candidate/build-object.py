"""One private core.o from the exact Image503 W=1 command; no make/link."""
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
BASE = Path('/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01')
OUT = Path('/home/cy122/charging-management-20261023/dwc-pm-susphy-object-01')


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for data in iter(lambda: stream.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()


def save(p, value):
    p.write_text(json.dumps(value, indent=2)+'\n')


def main():
    if sys.flags.optimize or os.geteuid() != 0:
        raise SystemExit('Requires nonoptimized Ubuntu/root')
    tests = json.loads((HERE/'test-result.json').read_bytes())
    assert tests['passed'] and tests['summary']['cases'] == 24
    for name, digest in tests['files'].items():
        assert sha(HERE/name) == digest, name
    source = json.loads((HERE/'source-result.json').read_bytes())
    expected = {'core.c':source['original_core_sha256'],
                'core.h':source['Image503_core_h_sha256'],
                'gadget.c':source['Image503_gadget_sha256']}
    assert not OUT.exists(), 'Unique output only; no replay'
    helper = REF/'kernel284/storage.py'
    assert sha(helper) == '5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
    pre_mount = Path('/proc/self/mountinfo').read_bytes()
    spec = importlib.util.spec_from_file_location('storage284_dwc_pm_object', helper)
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    shared = storage.mounted_build()
    original = shared.parent/'source354'
    post_mount = Path('/proc/self/mountinfo').read_bytes()
    for name, digest in expected.items():
        assert sha(BASE/'source354/drivers/usb/dwc3'/name) == digest, name
    assert sha(BASE/'build/.config') == '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
    cmdpath = BASE/'build/drivers/usb/dwc3/.core.o.cmd'
    tracked = [helper, cmdpath,
               *[BASE/'build'/n for n in ['.config','Module.symvers','arch/arm64/boot/Image','drivers/usb/dwc3/core.o']],
               *[BASE/'source354/drivers/usb/dwc3'/n for n in ['core.c','core.h','gadget.c','Makefile']],
               *[shared/n for n in ['.config','Module.symvers','arch/arm64/boot/Image','drivers/usb/dwc3/core.o']],
               *[original/'drivers/usb/dwc3'/n for n in ['core.c','core.h','gadget.c','Makefile']]]
    before = {str(p):sha(p) for p in tracked}
    OUT.mkdir(parents=True)
    (OUT/'mountinfo-before-helper.txt').write_bytes(pre_mount)
    (OUT/'mountinfo-after-helper.txt').write_bytes(post_mount)
    view, build = OUT/'source-view', OUT/'build'

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
    candidate = view/'drivers/usb/dwc3/core.c'
    candidate.unlink()  # Only the new, private symlink, never the source target.
    shutil.copy2(HERE/'core.c', candidate)
    assert not candidate.is_symlink() and candidate.stat().st_nlink == 1
    assert sha(candidate) == source['candidate_core_sha256']
    (build/'drivers/usb/dwc3').mkdir(parents=True)
    for name in ['include','arch/arm64/include/generated']:
        shutil.copytree(BASE/'build'/name, build/name)
    shutil.copy2(BASE/'build/.config', build/'.config')
    raw = cmdpath.read_text().splitlines()[0].split(':=',1)[1].strip()
    assert raw.count('/mnt/samurai-full282/source354/drivers/usb/dwc3/core.c') == 1
    assert '-DKBUILD_EXTRA_WARN1' in raw and '-Wextra' in raw
    raw = raw.replace('/mnt/samurai-full282/source354', str(view))
    argv = shlex.split(raw)
    assert argv[0] == 'aarch64-linux-gnu-gcc'
    assert argv[-1] == str(candidate)
    assert argv[argv.index('-o')+1] == 'drivers/usb/dwc3/core.o'
    assert not set(argv).intersection({';','&&','||','|'}), 'Single compiler argv only'
    argv.insert(1, '-Werror')
    save(OUT/'actual-command.json', argv)
    started = time.monotonic()
    parent_error = None
    rc = None
    with (OUT/'stdout.log').open('w') as stdout, (OUT/'stderr.log').open('w') as stderr:
        proc = subprocess.Popen(argv, cwd=build, stdout=stdout, stderr=stderr)
        try:
            save(OUT/'process-start.json', dict(pid=proc.pid, argv=argv, cwd=str(build)))
            print(json.dumps(dict(phase='compile',pid=proc.pid,private_output=str(OUT))),flush=True)
        except BaseException as exc:
            parent_error = repr(exc)
        finally:
            # Always own and wait this one compiler. No timeout, kill or retry.
            rc = proc.wait()
    after = {str(p):sha(p) for p in tracked}
    diagnostics = [s for s in (OUT/'stderr.log').read_text().splitlines()
                   if re.search(r'warning:|error:',s,re.I)]
    obj = build/'drivers/usb/dwc3/core.o'
    elf_header = obj.open('rb').read(20) if obj.exists() else b''
    aarch64_relocatable = (elf_header[:6] == b'\x7fELF\x02\x01' and
                           elf_header[16:20] == b'\x01\x00\xb7\x00')
    source_pins = {n:sha(view/'drivers/usb/dwc3'/n) for n in expected}
    assert source_pins == dict(expected, **{'core.c':source['candidate_core_sha256']})
    mount_after = Path('/proc/self/mountinfo').read_bytes()
    passed = (rc == 0 and parent_error is None and not diagnostics and before == after and
              post_mount == mount_after and aarch64_relocatable)
    result = dict(passed=passed,phase=dict(pid=proc.pid,terminal=True,returncode=rc,
                  seconds=time.monotonic()-started),parent_error=parent_error,
                  private_output=str(OUT),object_path=str(obj),object_sha256=sha(obj) if obj.exists() else None,
                  object_size=obj.stat().st_size if obj.exists() else None,
                  aarch64_relocatable=aarch64_relocatable,command=argv,
                  command_json_sha256=sha(OUT/'actual-command.json'),saved_command_source=str(cmdpath),
                  saved_command_sha256=sha(cmdpath),
                  compiler_version=subprocess.check_output([argv[0],'-dumpfullversion','-dumpversion'],text=True).strip(),
                  diagnostic_lines=diagnostics,stdout_sha256=sha(OUT/'stdout.log'),stderr_sha256=sha(OUT/'stderr.log'),
                  sources=source_pins,files={n:sha(HERE/n) for n in ['build-object.py','test-result.json','core.c']},
                  inputs_before=before,inputs_after=after,tracked_inputs_unchanged=before==after,
                  mount_before_helper_sha256=hashlib.sha256(pre_mount).hexdigest(),
                  mount_after_helper_sha256=hashlib.sha256(post_mount).hexdigest(),
                  original_helper_restored_mount=pre_mount!=post_mount,
                  parent_mounts_unchanged_after_helper=post_mount==mount_after,
                  parent_mountinfo_sha256=hashlib.sha256(mount_after).hexdigest(),
                  no_make=True,no_link=True,no_Image=True,no_ko=True,no_SDK=True,no_device=True,
                  full_resume_error_unwind_complete=False)
    save(HERE/'build-result.json', result)
    save(OUT/'result.json', result)
    print(json.dumps({k:result[k] for k in ['passed','phase','object_sha256','object_size',
                 'diagnostic_lines','tracked_inputs_unchanged','parent_mounts_unchanged_after_helper']}),flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
