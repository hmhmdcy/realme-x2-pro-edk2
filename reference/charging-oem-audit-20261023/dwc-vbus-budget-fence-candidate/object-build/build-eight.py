"""Eight explicit private compiler invocations from actual #502 commands, no make/link."""
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
LEAF = HERE.parent
REF = LEAF.parents[1]
BASE = Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')
OUT = Path('/home/cy122/charging-management-20261023/dwc-vbus-budget-fence-objects-01')
TARGETS = ['drivers/usb/dwc3/'+name+'.o' for name in
           ['core','trace','gadget','ep0','debugfs','dwc3-qcom','dwc3-qcom-legacy','dwc3-generic-plat']]


def sha(p):
    digest = hashlib.sha256()
    with p.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def save(p, value):
    p.write_text(json.dumps(value,indent=2)+'\n')


def main():
    assert sys.argv[1:] == ['--execute'], 'Explicit --execute required'
    if sys.flags.optimize or os.geteuid() != 0:
        raise RuntimeError('explicit nonoptimized Ubuntu/root required')
    assert not OUT.exists(), 'Unique output; retain and follow any existing process'
    assert sha(LEAF/'delivery.json') == '8d7a963a3aef17a16ef5e8ec19d96b31de4f066b261e315d28727c6d0b1e16aa'
    delivery = json.loads((LEAF/'delivery.json').read_bytes())
    for name, item in delivery['files'].items():
        assert sha(LEAF/name) == item['sha256'], name
    source = json.loads((LEAF/'source-result.json').read_bytes())
    for name, digest in source['candidate'].items():
        assert sha(LEAF/name) == digest, name
    public502 = REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate'
    original_result_path = public502/'build-result.json'
    assert sha(original_result_path) == 'feb6fd2e8ef8ca380f48a6f8f88b131646a874fa1d8660c3bde83a38ec8940e6'
    original_result = json.loads(original_result_path.read_bytes())
    assert original_result['passed'] and original_result['child_returncode'] == 0
    assert sha(BASE/'result.json') == sha(original_result_path)
    helper = REF/'kernel284/storage.py'
    assert sha(helper) == '5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
    before_helper = Path('/proc/self/mountinfo').read_bytes()
    spec = importlib.util.spec_from_file_location('storage284_dwc_budget_objects',helper)
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    shared = storage.mounted_build()
    shared_source = shared.parent/'source354'
    mount_before = Path('/proc/self/mountinfo').read_bytes()
    assert sha(BASE/'build/.config') == '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
    originals = {'core.c':'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf',
                 'gadget.c':'9eec86e42945a786447e6a6548a25b495e29a01bed8e8fbfc13e02903e1ff0c5',
                 'core.h':'525c1d5d8d0e501f4a92ddd6232961542b5c04521f29a50b8acf9ee86c41373c'}
    for name, digest in originals.items():
        assert sha(BASE/'source354/drivers/usb/dwc3'/name) == digest, name
    for name in ['vmlinux','arch/arm64/boot/Image']:
        assert sha(BASE/'build'/name) == original_result['build']['outputs'][name]['sha256'], name
    scope_path = REF/'charging-session-20261023/dwc-start-recovery-image-integration-plan/dependency-result.json'
    assert sha(scope_path) == 'bec66bdf580ce4541f19b60fb5f4865649f48376ba5bbfcc159424455fef8b46'
    scope = json.loads(scope_path.read_bytes())
    assert scope['passed'] and set(scope['required_object_targets']) == set(TARGETS)
    rows = {row['target']:row for row in scope['core_h_dependencies']}
    for target in TARGETS:
        row = rows[target]
        assert sha(BASE/'build'/target) == row['object_sha256'], target
        assert sha(BASE/'build'/row['cmd_path']) == row['cmd_sha256'], target
        assert sha(BASE/'source354'/row['source_path']) == row['source_sha256'], target
    cmdpaths = [BASE/'build'/rows[target]['cmd_path'] for target in TARGETS]
    base_sources = [BASE/'source354'/rows[target]['source_path'] for target in TARGETS]
    tracked = [helper, original_result_path, scope_path, LEAF/'delivery.json', LEAF/'test-result.json',
        *[LEAF/name for name in ['core.c','core.h','gadget.c']],
        *[BASE/'build'/name for name in ['.config','Module.symvers','vmlinux.symvers','include/generated/autoconf.h','vmlinux','arch/arm64/boot/Image',*TARGETS]],
        *cmdpaths,*base_sources,BASE/'source354/drivers/usb/dwc3/core.h',
        BASE/'source354/drivers/usb/dwc3/Makefile',
        *[shared/name for name in ['.config','Module.symvers','vmlinux','arch/arm64/boot/Image',*TARGETS]],
        *[shared_source/'drivers/usb/dwc3'/name for name in ['core.c','gadget.c','core.h','Makefile']]]
    before = {str(p):sha(p) for p in tracked}
    OUT.mkdir(parents=True)
    (OUT/'mountinfo-before-helper.txt').write_bytes(before_helper)
    (OUT/'mountinfo-before-build.txt').write_bytes(mount_before)
    view, build = OUT/'source-view', OUT/'build'

    def branch(src,dst,selected):
        dst.mkdir()
        for p in src.iterdir():
            if p.name == '.git':
                continue
            if p.name in selected:
                branch(p,dst/p.name,selected[p.name])
            else:
                (dst/p.name).symlink_to(p,target_is_directory=p.is_dir())

    phases = []
    parent_error = None
    try:
        branch(BASE/'source354',view,{'drivers':{'usb':{'dwc3':{}}}})
        copies = {'gadget.c':LEAF/'gadget.c','core.h':LEAF/'core.h',
                  'core.c':LEAF/'core.c'}
        for name, original in copies.items():
            target = view/'drivers/usb/dwc3'/name
            assert target.is_symlink()
            target.unlink()  # Only this new private symlink; no shared target mutation.
            shutil.copy2(original,target)
            assert not target.is_symlink() and target.stat().st_nlink == 1
            assert sha(target) == sha(original)
        (build/'drivers/usb/dwc3').mkdir(parents=True)
        for name in ['include','arch/arm64/include/generated']:
            shutil.copytree(BASE/'build'/name,build/name)
        shutil.copy2(BASE/'build/.config',build/'.config')
        commands = []
        for target in TARGETS:
            row = rows[target]
            cmdpath = BASE/'build'/row['cmd_path']
            raw = cmdpath.read_text().splitlines()[0].split(':=',1)[1].strip()
            assert raw == row['saved_compile_command'].strip(), target
            assert '-DKBUILD_EXTRA_WARN1' in raw and '-Wextra' in raw
            assert raw.count('/mnt/samurai-full282/source354/'+row['source_path']) == 1
            argv = shlex.split(raw.replace('/mnt/samurai-full282/source354',str(view)))
            assert argv[0] == 'aarch64-linux-gnu-gcc' and argv[-1] == str(view/row['source_path'])
            assert argv[argv.index('-o')+1] == target
            assert not set(argv).intersection({';','&&','||','|'})
            argv.insert(1,'-Werror')
            commands.append(dict(target=target,argv=argv,saved_command_path=str(cmdpath),
                saved_command_sha256=sha(cmdpath),source_sha256=sha(view/row['source_path'])))
        save(OUT/'commands.json',commands)
        for command in commands:
            name = Path(command['target']).stem
            started = time.monotonic()
            with (OUT/(name+'.stdout')).open('wb') as stdout,(OUT/(name+'.stderr')).open('wb') as stderr:
                child = subprocess.Popen(command['argv'],cwd=build,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                try:
                    save(OUT/'current-process.json',dict(pid=child.pid,argv=command['argv'],target=command['target'],terminal=False))
                    print(json.dumps(dict(phase='compile',target=command['target'],pid=child.pid)),flush=True)
                except BaseException as exc:
                    parent_error = repr(exc)
                finally:
                    rc = child.wait()  # Same real child; never timeout/replay or start another compiler on unknown state.
            obj = build/command['target']
            head = obj.open('rb').read(20) if obj.exists() else b''
            diagnostics = [line for line in (OUT/(name+'.stderr')).read_text().splitlines()
                           if re.search(r'warning:|error:',line,re.I)]
            phase = dict(target=command['target'],pid=child.pid,terminal=True,returncode=rc,
                seconds=time.monotonic()-started,object_path=str(obj),
                object_sha256=sha(obj) if obj.exists() else None,object_bytes=obj.stat().st_size if obj.exists() else None,
                aarch64_relocatable=head[:6]==b'\x7fELF\x02\x01' and head[16:20]==b'\x01\x00\xb7\x00',
                diagnostic_lines=diagnostics,stdout_sha256=sha(OUT/(name+'.stdout')),
                stderr_sha256=sha(OUT/(name+'.stderr')))
            phases.append(phase)
            save(OUT/'phases.json',phases)
            save(OUT/'current-process.json',dict(phase,argv=command['argv']))
            if rc or diagnostics or parent_error or not phase['aarch64_relocatable']:
                break
    except BaseException as exc:
        parent_error = repr(exc)
    finally:
        after = {str(p):sha(p) for p in tracked}
        mount_after = Path('/proc/self/mountinfo').read_bytes()
        (OUT/'mountinfo-after-build.txt').write_bytes(mount_after)
        sources = {name:sha(view/'drivers/usb/dwc3'/name) for name in originals} if view.exists() else {}
        passed = (parent_error is None and len(phases)==8 and before==after and mount_before==mount_after and
                  all(p['returncode']==0 and not p['diagnostic_lines'] and p['aarch64_relocatable'] for p in phases))
        result = dict(passed=passed,private_output=str(OUT),parent_error=parent_error,phases=phases,
            source_delivery_sha256=sha(LEAF/'delivery.json'),files={'build-eight.py':sha(HERE/'build-eight.py')},
            copied_sources=sources,original_source502=originals,inputs_before=before,inputs_after=after,
            tracked_source502_shared_inputs_unchanged=before==after,
            parent_mounts_unchanged_after_original_helper=mount_before==mount_after,
            original_helper_restored_mount=before_helper!=mount_before,
            original_helper_sha256=sha(helper),source_502_build_receipt_sha256=sha(original_result_path),
            compiler_version=subprocess.check_output(['aarch64-linux-gnu-gcc','-dumpfullversion','-dumpversion'],text=True).strip(),
            actual_commands_sha256=sha(OUT/'commands.json') if (OUT/'commands.json').exists() else None,
            requested_targets=TARGETS,old_suites_rerun=False,no_make=True,no_link=True,no_Image=True,no_module=True,
            software_budget_only=True,PM_unwind_complete=False,device_SSH_USB_SDK_Git_used=False)
        save(OUT/'build-result.json',result)
        save(HERE/'build-result.json',result)
        print(json.dumps(dict(passed=passed,parent_error=parent_error,terminal_objects=len(phases),
            tracked_inputs_unchanged=before==after,mounts_unchanged=mount_before==mount_after,
            receipt_sha256=sha(HERE/'build-result.json'))),flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
