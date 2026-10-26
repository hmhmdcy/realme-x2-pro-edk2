"""Eight explicit private compiler invocations from #503 commands, no make/link."""
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
BASE = Path('/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01')
OUT = Path('/home/cy122/charging-management-20261023/dwc-device-resume-outcome-objects-01')
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
    if sys.flags.optimize or os.geteuid() != 0:
        raise RuntimeError('explicit nonoptimized Ubuntu/root required')
    assert not OUT.exists(), 'Unique output; retain and follow any existing process'
    assert sha(LEAF/'delivery.json') == '293a2e962499e9e02a6062b2014fe23ea6e69932761cb2412c4c4b77dc0987d6'
    delivery = json.loads((LEAF/'delivery.json').read_bytes())
    for name, item in delivery['files'].items():
        assert sha(LEAF/name) == item['sha256'], name
    source = json.loads((LEAF/'source-result.json').read_bytes())
    for name, digest in source['source_inputs'].items():
        assert sha(REF/name) == digest, name
    public503 = REF/'charging-session-20261023/dwc-image503-start-recovery-candidate'
    assert sha(public503/'delivery.json') == 'e4e059334aab56acd8dde25348ba19aec2af9790b93fb632295e5b63a4ef9374'
    original_delivery = json.loads((public503/'delivery.json').read_bytes())
    assert sha(public503/'build-result.json') == original_delivery['files']['build-result.json']
    original_result = json.loads((public503/'build-result.json').read_bytes())
    assert original_result['passed'] and original_result['child_returncode'] == 0
    assert json.loads((BASE/'namespace-process.json').read_bytes())['terminal']
    assert json.loads((BASE/'namespace-process.json').read_bytes())['returncode'] == 0
    helper = REF/'kernel284/storage.py'
    assert sha(helper) == '5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
    before_helper = Path('/proc/self/mountinfo').read_bytes()
    spec = importlib.util.spec_from_file_location('storage284_dwc_outcome_objects',helper)
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    shared = storage.mounted_build()
    shared_source = shared.parent/'source354'
    mount_before = Path('/proc/self/mountinfo').read_bytes()
    assert sha(BASE/'build/.config') == '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
    originals = {'core.c':'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf',
                 'gadget.c':'ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314',
                 'core.h':'9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'}
    for name, digest in originals.items():
        assert sha(BASE/'source354/drivers/usb/dwc3'/name) == digest, name
    for name in [*TARGETS,'vmlinux','arch/arm64/boot/Image']:
        assert sha(BASE/'build'/name) == original_delivery['outputs'][name]['sha256'], name
    scope_path = REF/'charging-session-20261023/dwc-start-recovery-image-integration-plan/dependency-result.json'
    scope = json.loads(scope_path.read_bytes())
    assert scope['passed'] and set(scope['required_object_targets']) == set(TARGETS)
    rows = {row['target']:row for row in scope['core_h_dependencies']}
    cmdpaths = [BASE/'build'/rows[target]['cmd_path'] for target in TARGETS]
    base_sources = [BASE/'source354'/rows[target]['source_path'] for target in TARGETS]
    tracked = [helper, public503/'build-result.json', public503/'delivery.json', scope_path,
        *[BASE/'build'/name for name in ['.config','Module.symvers','vmlinux','arch/arm64/boot/Image',*TARGETS]],
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
                  'core.c':REF/'charging-ui-audit-20261023/dwc-pm-error-unwind-candidate/core.c'}
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
            copied_sources=sources,original_source503=originals,inputs_before=before,inputs_after=after,
            tracked_source503_shared_inputs_unchanged=before==after,
            parent_mounts_unchanged_after_original_helper=mount_before==mount_after,
            original_helper_restored_mount=before_helper!=mount_before,
            original_helper_sha256=sha(helper),source_503_delivery_sha256=sha(public503/'delivery.json'),
            compiler_version=subprocess.check_output(['aarch64-linux-gnu-gcc','-dumpfullversion','-dumpversion'],text=True).strip(),
            actual_commands_sha256=sha(OUT/'commands.json') if (OUT/'commands.json').exists() else None,
            requested_targets=TARGETS,old_suites_rerun=False,no_make=True,no_link=True,no_Image=True,no_module=True,
            PM_unwind_complete=False,device_SSH_USB_SDK_Git_used=False)
        save(OUT/'build-result.json',result)
        save(HERE/'build-result.json',result)
        print(json.dumps(dict(passed=passed,parent_error=parent_error,terminal_objects=len(phases),
            tracked_inputs_unchanged=before==after,mounts_unchanged=mount_before==mount_after,
            receipt_sha256=sha(HERE/'build-result.json'))),flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
