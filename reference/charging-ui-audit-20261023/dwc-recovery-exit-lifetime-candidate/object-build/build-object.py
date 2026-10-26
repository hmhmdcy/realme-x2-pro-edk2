"""One private gadget.o; the changed header is not mixed into an old Image."""
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
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent
REF=SOURCE.parents[1]
BASE=Path('/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01')
OUT=Path('/home/cy122/charging-management-20261023/dwc-recovery-exit-lifetime-object-01')


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def save(p,value):p.write_text(json.dumps(value,indent=2)+'\n')


def main():
    if sys.flags.optimize or os.geteuid()!=0:raise RuntimeError('Nonoptimized Ubuntu/root required')
    if sha(SOURCE/'source-delivery.json')!='4a645839ece5fd0273b3ff93beda9616593e94dc69215e9822295c76b6f26f07':
        raise ValueError('Frozen source delivery')
    source=json.loads((SOURCE/'source-delivery.json').read_bytes())
    for name,item in source['files'].items():
        if sha(SOURCE/name)!=item['sha256']:raise ValueError(name)
    if OUT.exists():raise RuntimeError('Unique private output only, no replay')
    helper=REF/'kernel284/storage.py'
    if sha(helper)!='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c':
        raise ValueError('Original storage guard')
    mounts_before=Path('/proc/self/mountinfo').read_bytes()
    spec=importlib.util.spec_from_file_location('storage284_dwc_exit_object',helper)
    storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
    shared=storage.mounted_build();original=shared.parent/'source354'
    mounts_after_helper=Path('/proc/self/mountinfo').read_bytes()
    baseline={'core.c':'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf',
              'gadget.c':'ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314',
              'core.h':'9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'}
    for n,h in baseline.items():
        if sha(BASE/'source354/drivers/usb/dwc3'/n)!=h:raise ValueError('Baseline '+n)
    if sha(BASE/'build/.config')!='23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed':
        raise ValueError('Original config')
    cmdpath=BASE/'build/drivers/usb/dwc3/.gadget.o.cmd'
    tracked=[helper,cmdpath,SOURCE/'source-delivery.json',
      *[BASE/'build'/n for n in ['.config','Module.symvers','arch/arm64/boot/Image','drivers/usb/dwc3/gadget.o']],
      *[BASE/'source354/drivers/usb/dwc3'/n for n in ['core.c','core.h','gadget.c','Makefile']],
      *[shared/n for n in ['.config','Module.symvers','arch/arm64/boot/Image','drivers/usb/dwc3/gadget.o']],
      *[original/'drivers/usb/dwc3'/n for n in ['core.c','core.h','gadget.c','Makefile']]]
    before={str(p):sha(p) for p in tracked}
    OUT.mkdir(parents=True)
    (OUT/'mountinfo-before-helper.txt').write_bytes(mounts_before)
    (OUT/'mountinfo-after-helper.txt').write_bytes(mounts_after_helper)
    view,build=OUT/'source-view',OUT/'build'

    def branch(src,dst,selected):
        dst.mkdir()
        for p in src.iterdir():
            if p.name=='.git':continue
            q=dst/p.name
            if p.name in selected:branch(p,q,selected[p.name])
            else:q.symlink_to(p,target_is_directory=p.is_dir())

    branch(BASE/'source354',view,{'drivers':{'usb':{'dwc3':{}}}})
    copies={'gadget.c':SOURCE/'gadget.c','core.h':SOURCE/'core.h',
            'core.c':SOURCE.parent/'dwc-pm-error-unwind-candidate/core.c'}
    wanted={'gadget.c':'f32623e0bd1bdad968f84b08da28389d4d939b87ae18abcc850ccb4643640557',
            'core.h':'b177e605cddbd0bb3a7501b3a5afe7b94a58d0027569ba08e42fbfddfdae62e4',
            'core.c':'5331ae946cde894e2da484df5b8fbc6d386d117a60ad0e3dac5a1ebaaec6a17f'}
    for n,p in copies.items():
        if sha(p)!=wanted[n]:raise ValueError('Candidate '+n)
        q=view/'drivers/usb/dwc3'/n;q.unlink() # New private symlink only.
        shutil.copy2(p,q)
        if q.is_symlink() or q.stat().st_nlink!=1 or sha(q)!=wanted[n]:raise ValueError('Private '+n)
    (build/'drivers/usb/dwc3').mkdir(parents=True)
    for n in ['include','arch/arm64/include/generated']:shutil.copytree(BASE/'build'/n,build/n)
    shutil.copy2(BASE/'build/.config',build/'.config')
    raw=cmdpath.read_text().splitlines()[0].split(':=',1)[1].strip()
    if raw.count('/mnt/samurai-full282/source354/drivers/usb/dwc3/gadget.c')!=1:
        raise ValueError('Saved gadget command source')
    if '-DKBUILD_EXTRA_WARN1' not in raw or '-Wextra' not in raw:raise ValueError('Saved W1 command')
    argv=shlex.split(raw.replace('/mnt/samurai-full282/source354',str(view)))
    if argv[0]!='aarch64-linux-gnu-gcc' or argv[-1]!=str(view/'drivers/usb/dwc3/gadget.c'):
        raise ValueError('Exact compiler and source')
    if argv[argv.index('-o')+1]!='drivers/usb/dwc3/gadget.o':raise ValueError('Single object')
    if set(argv).intersection({';','&&','||','|'}):raise ValueError('Shell separator')
    argv.insert(1,'-Werror');save(OUT/'actual-command.json',argv)
    started=time.monotonic();parent_error=None
    with (OUT/'stdout.log').open('w') as stdout,(OUT/'stderr.log').open('w') as stderr:
        proc=subprocess.Popen(argv,cwd=build,stdout=stdout,stderr=stderr)
        try:
            save(OUT/'process-start.json',dict(pid=proc.pid,argv=argv,cwd=str(build)))
            print(json.dumps(dict(phase='compile',pid=proc.pid,private_output=str(OUT))),flush=True)
        except BaseException as exc:parent_error=repr(exc)
        finally:rc=proc.wait() # Same sole compiler, no kill/timeout/retry.
    after={str(p):sha(p) for p in tracked}
    diagnostics=[s for s in (OUT/'stderr.log').read_text().splitlines() if re.search(r'warning:|error:',s,re.I)]
    obj=build/'drivers/usb/dwc3/gadget.o'
    elf=b''
    if obj.exists():
        with obj.open('rb') as stream:elf=stream.read(20)
    arm64=elf[:6]==b'\x7fELF\x02\x01' and elf[16:20]==b'\x01\x00\xb7\x00'
    actual_sources={n:sha(view/'drivers/usb/dwc3'/n) for n in wanted}
    mounts_final=Path('/proc/self/mountinfo').read_bytes()
    passed=(rc==0 and parent_error is None and not diagnostics and arm64 and
            before==after and actual_sources==wanted and mounts_after_helper==mounts_final)
    result=dict(passed=passed,phase=dict(pid=proc.pid,terminal=True,returncode=rc,seconds=time.monotonic()-started),
      parent_error=parent_error,private_output=str(OUT),object_path=str(obj),object_sha256=sha(obj) if obj.exists() else None,
      object_size=obj.stat().st_size if obj.exists() else None,aarch64_relocatable=arm64,command=argv,
      command_json_sha256=sha(OUT/'actual-command.json'),saved_command_source=str(cmdpath),
      saved_command_sha256=sha(cmdpath),compiler_version=subprocess.check_output([argv[0],'-dumpfullversion','-dumpversion'],text=True).strip(),
      diagnostic_lines=diagnostics,stdout_sha256=sha(OUT/'stdout.log'),stderr_sha256=sha(OUT/'stderr.log'),
      sources=actual_sources,source_delivery_sha256=sha(SOURCE/'source-delivery.json'),
      inputs_before=before,inputs_after=after,tracked_inputs_unchanged=before==after,
      mount_before_helper_sha256=hashlib.sha256(mounts_before).hexdigest(),
      mount_after_helper_sha256=hashlib.sha256(mounts_after_helper).hexdigest(),
      original_helper_restored_mount=mounts_before!=mounts_after_helper,
      parent_mounts_unchanged_after_helper=mounts_after_helper==mounts_final,
      parent_mountinfo_sha256=hashlib.sha256(mounts_final).hexdigest(),
      files={'build-object.py':sha(HERE/'build-object.py')},single_target_only=True,
      new_struct_layout_all_consumers_rebuilt=False,no_make=True,no_link=True,no_Image=True,no_ko=True,
      no_SDK=True,no_device=True,full_resume_abort_complete=False)
    save(HERE/'build-result.json',result);save(OUT/'result.json',result)
    print(json.dumps({k:result[k] for k in ['passed','phase','object_sha256','object_size','diagnostic_lines',
                      'tracked_inputs_unchanged','parent_mounts_unchanged_after_helper']}),flush=True)
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
