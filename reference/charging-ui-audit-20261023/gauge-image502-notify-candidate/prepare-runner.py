"""Derive a separately reviewed 502 runner; preserve the frozen 501 runner."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
OLD = REF / 'charging-session-20261023/gauge-image501-repro-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(OLD / 'run-B.py') == 'afcb226e28bdbfaeb70153ce0a60e3353a121f952d2686ecb7032cf1ccd98b79'
original = (OLD / 'run-B.py').read_text()
text = original


def replace(old, new):
    global text
    assert text.count(old) == 1, old
    text = text.replace(old, new)


replace('"""Private B501 with original reproducible timestamp. No device or boot packaging."""',
        '"""Private Image502 from passed 501: BQ callback only, no boot packaging/device."""')
replace('import hashlib, importlib.util, json, os, shutil, subprocess, sys, time',
        'import hashlib, importlib.util, json, os, re, shutil, subprocess, sys, time')
replace('sys.dont_write_bytecode=True',
        "sys.dont_write_bytecode=True\nif sys.flags.optimize: raise RuntimeError('Non-optimized interpreter required')")
replace("BASELEAF=HERE.parent/'gauge-image363-baseline'",
        "BASELEAF=REF/'charging-session-20261023/gauge-image363-baseline'\nPREVIOUS=REF/'charging-session-20261023/gauge-image501-repro-candidate'")
replace("BASE=Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01')",
        "BASE=Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01')")
replace("OUT=Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01')",
        "OUT=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')")
replace("FAILED=Path('/home/cy122/charging-management-20261023/gauge-image501-B-01')",
        "ORIGINAL363=Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01')")
replace("FROZEN=REF/'charging-oem-audit-20261023/gauge-current-samurai-candidate/bq27xxx_battery.c'",
        "FROZEN=HERE.parent/'gauge-notify-immediate-candidate/bq27xxx_battery.c'")
replace("B_SHA='0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe'",
        "B_SHA='0014077792948460fc2a2e9581225dc684cba4d5bff95c3e88767d661ce5439b'")
replace("env.update(KBUILD_BUILD_VERSION='501',", "env.update(KBUILD_BUILD_VERSION='502',")
replace("metadata=proof_module.prove(BASE/'build',BUILD)", "metadata=proof_module.prove(BASE/'build',BUILD)")
replace("assert (BUILD/'.config').read_bytes()==(BASE/'config363-original').read_bytes()",
        "assert (BUILD/'.config').read_bytes()==(BASE/'build/.config').read_bytes()")
replace("assert '#501 SMP PREEMPT '", "assert '#502 SMP PREEMPT '")
replace("assert base.inventory(PAYLOAD)==json.loads((BASE/'initramfs-before.json').read_bytes())",
        "assert base.inventory(PAYLOAD)==json.loads((OUT/'input-initramfs363-baseline-before.json').read_bytes())")
replace("assert outputs['arch/arm64/boot/Image']['sha256']!=base.EXPECTED['Image']",
        "assert outputs['arch/arm64/boot/Image']['sha256']!='3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'")
replace("'KBUILD_BUILD_VERSION':'501'", "'KBUILD_BUILD_VERSION':'502'")
replace("failed_paths=[FAILED/'result.json',FAILED/'build/arch/arm64/boot/Image',FAILED/'build/vmlinux',\n                  FAILED/'build/usr/initramfs_data.cpio',FAILED/'build/usr/initramfs_inc_data',\n                  FAILED/'build/usr/initramfs_data.o',FAILED/'source354'/REL]",
        "original363_paths=[ORIGINAL363/'result.json',ORIGINAL363/'build/arch/arm64/boot/Image',ORIGINAL363/'build/vmlinux',\n                  ORIGINAL363/'build/usr/initramfs_data.cpio',ORIGINAL363/'build/usr/initramfs_inc_data',\n                  ORIGINAL363/'build/usr/initramfs_data.o',ORIGINAL363/'source354'/REL]")
text = text.replace('failed_before', 'original363_before').replace('failed_after', 'original363_after').replace('failed_paths', 'original363_paths')
text = text.replace("'failed_originals_before'", "'original363_before'").replace("'failed_originals_after'", "'original363_after'").replace("'failed_originals_preserved'", "'original363_preserved'")
replace("'--child',str(os.getpid()),parent_ns,mount_sha]", "'--child',str(os.getpid()),parent_ns,mount_sha]")
replace("str(HERE/'run-B.py')", "str(HERE/'run-502.py')")
replace("assert sys.argv[1:]==['--execute-B'],'Explicit --execute-B required'",
        "if not sys.argv[1:] or sys.argv[1:]==['--check-local']:\n        check_local(); print(json.dumps({'passed':True,'mode':'check-local','storage_or_build_invoked':False})); raise SystemExit(0)\n    assert sys.argv[1:]==['--execute-502'],'Explicit --execute-502 required'")
replace("    assert os.getuid()==0 and not OUT.exists(),'Unique output exists; no replay'",
        "    check_local()\n    assert not sys.flags.optimize, 'Non-optimized interpreter required'\n    assert os.getuid()==0 and not OUT.exists(),'Unique output exists; no replay'\n    assert not (HERE/'build-result.json').exists(), 'Do not overwrite original receipt'")
replace("    assert storage.mounted_build()==BUILD",
        "    assert sha(REF/'kernel284/storage.py')=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'\n    assert storage.mounted_build()==BUILD\n    previous=json.loads((PREVIOUS/'build-result.json').read_bytes())\n    assert previous['passed'] and sha(BASE/'result.json')==sha(PREVIOUS/'build-result.json')\n    assert json.loads((BASE/'namespace-process.json').read_bytes())['terminal']\n    assert json.loads((BASE/'namespace-process.json').read_bytes())['returncode']==0\n    assert sha(BASE/'source354'/REL)=='0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe'\n    assert all(sha(BASE/'build'/n)==row['sha256'] for n,row in previous['build']['outputs'].items())\n    assert previous['build']['builtin_exports_exact_original_rows']\n    link=json.loads((base.PLAN/'link-inputs.json').read_bytes())\n    for name,row in link['toolchains'].items():\n        if row['path']: assert sha(Path(row['path']).resolve())==row['sha256'], name\n    for row in link['rust_toolchains']: assert sha(row['path'])==row['sha256']")
replace("    snapshots={};ret=None", "    snapshots={};ret=None;parent_error=None")
replace("            ret=process.wait();f.flush();os.fsync(f.fileno())",
        "            ret=process.wait();f.flush();os.fsync(f.fileno())")
replace("            state.update(phase=name,child_pid=process.pid,argv=argv)\n            save(OUT/'child-state.json',state)\n            event(name,started=True,child_pid=process.pid)\n            ret=process.wait();f.flush();os.fsync(f.fileno())",
        "            state.update(phase=name,child_pid=process.pid,argv=argv)\n            try:\n                save(OUT/'child-state.json',state)\n                event(name,started=True,child_pid=process.pid)\n            finally:\n                ret=process.wait()\n                state.update(last_child_terminal=True,last_child_returncode=ret)\n            f.flush();os.fsync(f.fileno())")
replace("        save(OUT/'namespace-process.json',{'pid':process.pid,'argv':argv,'terminal':False})\n        event('B-namespace-child-started',child_pid=process.pid,identity=identity)\n        ret=process.wait()",
        "        try:\n            save(OUT/'namespace-process.json',{'pid':process.pid,'argv':argv,'terminal':False})\n            event('B-namespace-child-started',child_pid=process.pid,identity=identity)\n        finally:\n            ret=process.wait()")
replace("    finally:\n        preserved={}", "    except BaseException as e:\n        parent_error=repr(e)\n        raise\n    finally:\n        preserved={}")
replace("'passed':ret==0 and all(preserved.values())", "'passed':parent_error is None and ret==0 and all(preserved.values())")
replace("'private_output':str(OUT),'child_returncode':ret,'baseline_trees_preserved':preserved,",
        "'private_output':str(OUT),'child_returncode':ret,'parent_error':parent_error,'baseline_trees_preserved':preserved,")
replace("        save(OUT/'closure-final.json',after)",
        "        save(OUT/'closure-final.json',after)\n        additional=prove_additional(after,leaves,stub)\n        save(OUT/'compatibility-result.json',additional)")
replace("'metadata_proof':metadata,'initramfs_exact_original_hashes':ramfs,",
        "'metadata_proof':metadata,'compatibility':additional,'initramfs_exact_original_hashes':ramfs,")

pins = {
    'charging-session-20261023/gauge-image501-repro-candidate/delivery.json': '616b2d35633c64bb6c2e395cbb437526d2340a9395f5d6a40128e9eb6da440fb',
    'charging-session-20261023/gauge-image501-repro-candidate/build-result.json': '9371adeeb28e2126d8b606ec6b30d11208722d8934d57ce1a023e77100c4cc35',
    'charging-session-20261023/gauge-image501-repro-candidate/abi-result.json': '3ed8fc61424cf82a0465a1876c8c2ec88d31b714accffa81d4f0f31c5f7ac25c',
    'charging-session-20261023/gauge-image501-abi-provider-supplement/result.json': 'db8dffd5443b1e60944ee33879283d530183ca832e29d6bb1e2f22b60fd483d2',
    'charging-ui-audit-20261023/gauge-notify-immediate-candidate/delivery.json': 'acb96a5e7908b12416309cfd47fad33a58ff8cd20e2a862e619eeffec5dff214',
}
for name, digest in pins.items():
    assert sha(REF / name) == digest
helpers = '''
def check_local():
    assert not sys.flags.optimize, 'Non-optimized interpreter required'
    pins=PIN_LITERAL
    for name,digest in pins.items(): assert sha(REF/name)==digest, name
    previous=json.loads((PREVIOUS/'delivery.json').read_bytes())
    for name,digest in previous['files'].items(): assert sha(PREVIOUS/name)==digest, name
    notify=HERE.parent/'gauge-notify-immediate-candidate'
    delivery=json.loads((notify/'delivery.json').read_bytes())
    assert delivery['passed']
    for name,digest in delivery['files'].items(): assert sha(notify/name)==digest, name
    assert sha(FROZEN)==B_SHA
    assert sha(HERE/'metadata-proof.py')=='31f22e48c033fc52ca380c8f1eb5d5737ba017fab5d0e8d8e7f4598abbcb4bcb'

def prove_additional(after,leaves,stub):
    old_inventory=json.loads((OUT/'build-baseline-before.json').read_bytes())
    old_objects={n:r['sha256'] for n,r in old_inventory.items() if n.endswith('.o') and r['kind']=='file'}
    current={str(p.relative_to(BUILD)):sha(p) for p in BUILD.rglob('*.o') if p.is_file() and not p.is_symlink()}
    delta=[{'path':n,'before':old_objects.get(n),'after':current.get(n)}
           for n in sorted(old_objects.keys()|current.keys()) if old_objects.get(n)!=current.get(n)]
    allowed={'.tmp_vmlinux1.kallsyms.o','.tmp_vmlinux2.kallsyms.o','drivers/power/supply/bq27xxx_battery.o',
             'init/version.o','init/version-timestamp.o','vmlinux.o'}
    assert {r['path'] for r in delta}==allowed, delta
    save(OUT/'all-object-delta.json',delta)
    source_before=json.loads((OUT/'source354-baseline-before.json').read_bytes())
    source_after=base.inventory(SOURCE)
    assert sorted(n for n in source_before.keys()|source_after.keys() if source_before.get(n)!=source_after.get(n))==[REL]
    def exports(path):
        rows=subprocess.check_output(['aarch64-linux-gnu-nm','-a','--defined-only',str(path)],text=True).splitlines()
        return {r.split()[-1].removeprefix('__ksymtab_') for r in rows
                if r.split()[-1].startswith('__ksymtab_') and r.split()[-1]!='__ksymtab_strings'}
    fresh_exports=symvers(BUILD/'vmlinux.symvers')
    old_exports=symvers(BASE/'build/vmlinux.symvers')
    assert fresh_exports==old_exports and exports(BASE/'build/vmlinux')==exports(BUILD/'vmlinux')==set(fresh_exports)
    assert sha(BUILD/'Module.symvers')==sha(BASE/'build/Module.symvers')=='0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223'
    def members(path):
        rows=subprocess.check_output(['aarch64-linux-gnu-ar','t',str(path)],text=True).splitlines()
        answer=[]
        for name in rows:
            p=Path(name)
            if not p.is_absolute(): p=path.parent/p
            answer.append(str(p.relative_to(BUILD)))
        return answer
    assert members(BUILD/'vmlinux.a')==list(leaves)
    assert members(BUILD/'drivers/firmware/efi/libstub/lib.a')==list(stub)
    param=[line.split() for line in subprocess.check_output(['aarch64-linux-gnu-nm','-a',str(BUILD/'drivers/power/supply/bq27xxx_battery.o')],text=True).splitlines()
           if line.split()[-1]=='samurai_instant_current']
    assert len(param)==1 and param[0][-2]=='b'
    diagnostics=[]
    for log in OUT.glob('B-*.log'):
        diagnostics.extend({'log':log.name,'line':line} for line in log.read_text(errors='replace').splitlines()
                           if re.search(r'\\b(?:warning|error):',line,re.I))
    assert not diagnostics, diagnostics
    return {'passed':True,'compared_to':'actual passed Image501 repro',
            'all_object_delta':delta,'builtin_export_count':len(fresh_exports),
            'actual_ELF_export_names_exact_501':True,'builtin_export_rows_exact_501':True,
            'Module_symvers_exact_501':True,'public_headers_unchanged':True,
            'archive_order_exact':True,'default_opt_in_zero_BSS':True,'diagnostics':diagnostics,
            'ABI_501_and_provider_supplement_reused':True,'module_scan_rerun':False,
            'type_ABI_or_runtime_attestation':False}

'''.replace('PIN_LITERAL', repr(pins))
replace('def symvers(path):', helpers + 'def symvers(path):')
text = text.replace("'B-bq-object'", "'B-bq-object'")
(HERE / 'run-502.py').write_bytes(text.encode())
proof = (OLD / 'metadata-proof.py').read_text()
assert sha(OLD / 'metadata-proof.py') == '221117fc8c26cc9d1311e8e9e370e2cce071216db1806e5714744f2f69946463'
proof = proof.replace("OLD_ID=b'#363 SMP", "OLD_ID=b'#501 SMP").replace("NEW_ID=b'#501 SMP", "NEW_ID=b'#502 SMP")
(HERE / 'metadata-proof.py').write_bytes(proof.encode())
(HERE / 'runner-vs-501.diff').write_bytes(''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
    'frozen501/run-B.py', 'image502/run-502.py')).encode())
compile(text, str(HERE / 'run-502.py'), 'exec')
compile(proof, str(HERE / 'metadata-proof.py'), 'exec')
print(json.dumps({'runner_sha256': sha(HERE / 'run-502.py'), 'metadata_sha256': sha(HERE / 'metadata-proof.py'),
                  'old_runner_unchanged': sha(OLD / 'run-B.py') == 'afcb226e28bdbfaeb70153ce0a60e3353a121f952d2686ecb7032cf1ccd98b79'}))
