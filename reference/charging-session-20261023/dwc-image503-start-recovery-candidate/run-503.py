"""Private consistent DWC Image503 from passed 502; no boot packaging/device."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, re, shutil, subprocess, sys, time
sys.dont_write_bytecode=True
if sys.flags.optimize: raise RuntimeError('Non-optimized interpreter required')
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
BASELEAF=REF/'charging-session-20261023/gauge-image363-baseline'
PREVIOUS=REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate'
BASE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')
OUT=Path('/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01')
ORIGINAL363=Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01')
FROZEN=HERE.parent/'dwc-device-start-recovery-candidate'
DWC_SOURCES={'drivers/usb/dwc3/gadget.c':'ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314',
             'drivers/usb/dwc3/core.h':'9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'}
METADATA_SHA='0b029754c347f93e18f285bc508c5f2625684498e5b78de453bb71dbe96ac7c9'
DWC_TARGETS=['drivers/usb/dwc3/'+n+'.o' for n in ['core','trace','gadget','ep0','debugfs',
             'dwc3-qcom','dwc3-qcom-legacy','dwc3-generic-plat']]
REL='drivers/power/supply/bq27xxx_battery.c'
B_SHA='0014077792948460fc2a2e9581225dc684cba4d5bff95c3e88767d661ce5439b'
RAMFS_EXPECTED={
 'usr/initramfs_data.cpio':'fc1d27728b2ab7dc8c08b3a372b9f1a025a9db60faaad6b33001398e214c9669',
 'usr/initramfs_inc_data':'319b665d4bdbf9647efb1ae1055438e5a7990c69e7016190c9625de414b81678',
 'usr/initramfs_data.o':'2524437833f58ecd8410d6c1d740d0f412faaae85d3ae73c63d3f1f3607484de'}
spec=importlib.util.spec_from_file_location('frozen_363_baseline',BASELEAF/'run-baseline.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
assert base.sha(BASELEAF/'run-baseline.py')=='136a60e4815014b4fc1afc221f2abfcd39935440def62af081059ee1e2b58650'
sha,save,event=base.sha,base.save,base.event
BUILD,SOURCE,PAYLOAD,TEMP=base.BUILD,base.SOURCE,base.PAYLOAD,base.TEMP


def check_local():
    assert not sys.flags.optimize, 'Non-optimized interpreter required'
    pins = {'charging-ui-audit-20261023/gauge-image502-notify-candidate/delivery.json': '4e27a8da005b3e5b41799f63a9a3b3e4de1b22f6d60f8a1172c2c28cd8163e21', 'charging-ui-audit-20261023/gauge-image502-notify-candidate/build-result.json': 'feb6fd2e8ef8ca380f48a6f8f88b131646a874fa1d8660c3bde83a38ec8940e6', 'charging-ui-audit-20261023/gauge-image502-notify-candidate/abi-reuse-result.json': 'b097ee9314bd7b913fd2ec08a462b6e04d8ed68c635a168080f4e035b149b230', 'charging-session-20261023/dwc-device-start-recovery-candidate/delivery.json': '1f3aa44fa29c8f901c39a378ff4a7d546c447c40072e3e5283226857cfcb1349', 'charging-oem-audit-20261023/dwc-device-start-recovery-independent-review/review-result.json': 'a6ce6a39e074b266e3e66c691686dbaeeda75baef480a4662848d9ef7ae70b8b', 'charging-session-20261023/dwc-start-recovery-image-integration-plan/delivery.json': '2767b2679738283b62d326b9192d59ed777a7b7741c5633fc37abfe6d8904174'}
    for name,digest in pins.items(): assert sha(REF/name)==digest,name
    for leaf in [PREVIOUS,FROZEN]:
        delivery=json.loads((leaf/'delivery.json').read_bytes())
        assert delivery['passed']
        for name,digest in delivery['files'].items(): assert sha(leaf/name)==digest,name
    for name,digest in DWC_SOURCES.items(): assert sha(FROZEN/Path(name).name)==digest,name
    assert sha(HERE/'metadata-proof.py')==METADATA_SHA

def prove_additional(after,leaves,stub):
    old_inventory=json.loads((OUT/'build-baseline-before.json').read_bytes())
    old_objects={n:r['sha256'] for n,r in old_inventory.items() if n.endswith('.o') and r['kind']=='file'}
    current={str(p.relative_to(BUILD)):sha(p) for p in BUILD.rglob('*.o') if p.is_file() and not p.is_symlink()}
    delta=[{'path':n,'before':old_objects.get(n),'after':current.get(n)}
           for n in sorted(old_objects.keys()|current.keys()) if old_objects.get(n)!=current.get(n)]
    metadata={'.tmp_vmlinux1.kallsyms.o','.tmp_vmlinux2.kallsyms.o','init/version.o','init/version-timestamp.o','vmlinux.o'}
    changed={r['path'] for r in delta}
    assert changed <= set(DWC_TARGETS)|metadata, delta
    assert metadata <= changed, delta
    save(OUT/'all-object-delta.json',delta)
    source_before=json.loads((OUT/'source354-baseline-before.json').read_bytes())
    source_after=base.inventory(SOURCE)
    assert sorted(n for n in source_before.keys()|source_after.keys() if source_before.get(n)!=source_after.get(n))==sorted(DWC_SOURCES)
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
                           if re.search(r'\b(?:warning|error):',line,re.I))
    assert not diagnostics, diagnostics
    object_log=(OUT/'B-dwc-eight-objects.log').read_text(errors='replace')
    actual_compiles={n:len(re.findall(r'-c -o '+re.escape(n)+r'(?=\s)',object_log)) for n in DWC_TARGETS}
    assert all(count==1 for count in actual_compiles.values()),actual_compiles
    save(OUT/'eight-compile-proof.json',actual_compiles)
    return {'passed':True,'eight_actual_compile_commands':actual_compiles,'compared_to':'actual passed Image502 notify',
            'all_object_delta':delta,'builtin_export_count':len(fresh_exports),
            'actual_ELF_export_names_exact_502':True,'builtin_export_rows_exact_502':True,
            'Module_symvers_exact_502':True,'public_headers_unchanged':True,
            'private_dwc_core_h_changed':True,'all_eight_dependency_targets_requested':True,
            'archive_order_exact':True,'default_opt_in_zero_BSS':True,'diagnostics':diagnostics,
            'ABI_501_and_provider_supplement_reused':True,'module_scan_rerun':False,
            'type_ABI_or_runtime_attestation':False}

def symvers(path):
    rows={}
    for line in path.read_text().splitlines():
        fields=line.split()
        if len(fields)>=4 and fields[2]=='vmlinux':
            assert fields[1] not in rows
            rows[fields[1]]=fields
    assert rows
    return rows

def child(parent_pid,parent_ns,parent_mount_sha):
    assert os.getuid()==0 and base.namespace()!=parent_ns
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    assert not any(any(t.startswith(('shared:','master:','propagate_from:')) for t in l.split()[6:l.split().index('-')]) for l in base.mounts())
    parent_hash=lambda:hashlib.sha256(('\n'.join(base.mounts(parent_pid))+'\n').encode()).hexdigest()
    assert parent_hash()==parent_mount_sha
    bindings=[]
    for target,name in [(SOURCE,'source354'),(BUILD,'build'),(PAYLOAD,'input-initramfs363'),(TEMP,'tmp')]:
        subprocess.run(['mount','--bind',str(OUT/name),str(target)],check=True)
        assert os.path.samefile(OUT/name,target)
        bindings.append({'target':str(target),'private':str(OUT/name),'inode':target.stat().st_ino})
    assert parent_hash()==parent_mount_sha
    save(OUT/'namespace-proof.json',{'parent_namespace':parent_ns,'child_namespace':base.namespace(),
         'recursive_private_verified':True,'bindings':bindings,'parent_mountinfo_unchanged_while_bound':True,'mountinfo':base.mounts()})
    identity=json.loads((OUT/'identity.json').read_bytes())
    env=base.build_environment()
    env.update(KBUILD_BUILD_VERSION='503',KBUILD_BUILD_TIMESTAMP=identity['KBUILD_BUILD_TIMESTAMP'])
    assert sha(SOURCE/REL)==B_SHA
    assert sha(BUILD/'.config')==base.EXPECTED['config']
    original=json.loads((BASE/'closure-final.json').read_bytes())
    commands=[];phases=[]
    state={'worker_pid':os.getpid(),'terminal':False,'private_output':str(OUT)}
    def run(name,argv):
        start=time.monotonic(); log=OUT/(name+'.log')
        commands.append({'phase':name,'argv':argv,'cwd':str(BUILD)})
        with log.open('xb') as f:
            process=subprocess.Popen(argv,cwd=BUILD,env=env,stdout=f,stderr=subprocess.STDOUT)
            state.update(phase=name,child_pid=process.pid,argv=argv)
            try:
                save(OUT/'child-state.json',state)
                event(name,started=True,child_pid=process.pid)
            finally:
                ret=process.wait()
                state.update(last_child_terminal=True,last_child_returncode=ret)
            f.flush();os.fsync(f.fileno())
        phases.append({'phase':name,'returncode':ret,'seconds':round(time.monotonic()-start,2),'log_sha256':sha(log)})
        save(OUT/'commands.json',commands);save(OUT/'phases.json',phases)
        event(name,returncode=ret,seconds=phases[-1]['seconds'])
        assert ret==0,(name,ret)
    try:
        argv=['make','-C',str(SOURCE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
              'LOCALVERSION=+','W=1','V=1','-j4']
        run('B-dwc-eight-objects',argv+DWC_TARGETS)
        run('B-image',argv+['Image'])
        after=base.closure()
        leaves=json.loads((base.PLAN/'link-inputs.json').read_bytes())['members']
        stub=json.loads((base.PLAN/'final-link-inputs.json').read_bytes())['libstub_members']
        delta=[{'path':n,'before':original.get(n),'after':after.get(n)} for n in sorted(original.keys()|after.keys()) if original.get(n)!=after.get(n)]
        leaf_delta=[r for r in delta if r['path'] in leaves]
        stub_delta=[r for r in delta if r['path'] in stub]
        save(OUT/'actual-link-input-delta.json',delta);save(OUT/'actual-leaf-delta.json',leaf_delta)
        save(OUT/'closure-final.json',after)
        additional=prove_additional(after,leaves,stub)
        save(OUT/'compatibility-result.json',additional)
        changed_leaf={r['path'] for r in leaf_delta}
        assert changed_leaf <= set(DWC_TARGETS)|{'init/version.o'},leaf_delta
        assert 'init/version.o' in changed_leaf and 'drivers/usb/dwc3/gadget.o' in changed_leaf,leaf_delta
        assert all(after[n]==original[n] for n in leaves if n not in set(DWC_TARGETS)|{'init/version.o'})
        assert not stub_delta
        assert after['init/version-timestamp.o']!=original['init/version-timestamp.o']
        # These remain real original bytes; no archive/header or object patching.
        ramfs={n:sha(BUILD/n) for n in ['usr/initramfs_data.cpio','usr/initramfs_inc_data','usr/initramfs_data.o']}
        assert ramfs==RAMFS_EXPECTED
        proof_spec=importlib.util.spec_from_file_location('metadata_proof',HERE/'metadata-proof.py')
        proof_module=importlib.util.module_from_spec(proof_spec);proof_spec.loader.exec_module(proof_module)
        metadata=proof_module.prove(BASE/'build',BUILD)
        save(OUT/'metadata-section-proof.json',metadata)
        old_exports=symvers(BASE/'build/Module.symvers')
        new_exports=symvers(BUILD/'vmlinux.symvers')
        save(OUT/'builtin-exports-original.json',old_exports);save(OUT/'builtin-exports-candidate.json',new_exports)
        assert old_exports==new_exports,'Export name/class/namespace/CRC/module rows changed'
        assert (BUILD/'.config').read_bytes()==(BASE/'build/.config').read_bytes()
        assert (BUILD/'include/config/kernel.release').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k363+'
        uts=(BUILD/'include/generated/utsversion.h').read_text()
        assert '#503 SMP PREEMPT '+identity['KBUILD_BUILD_TIMESTAMP'] in uts
        assert sha(SOURCE/REL)==B_SHA
        assert base.inventory(PAYLOAD)==json.loads((OUT/'input-initramfs363-baseline-before.json').read_bytes())
        outputs={n:{'sha256':sha(BUILD/n),'bytes':(BUILD/n).stat().st_size} for n in [
            'arch/arm64/boot/Image','vmlinux','System.map','vmlinux.symvers','drivers/power/supply/bq27xxx_battery.o',
            'init/version.o','init/version-timestamp.o',*DWC_TARGETS]}
        assert outputs['arch/arm64/boot/Image']['sha256']!='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'
        result={'passed':True,'identity':identity,'outputs':outputs,'source_sha256':B_SHA,
                'leaf_delta':leaf_delta,'unchanged_other_leaf_count':len(leaves)-9,'unchanged_libstub_count':len(stub),
                'metadata_proof':metadata,'compatibility':additional,'initramfs_exact_original_hashes':ramfs,
                'builtin_export_count':len(new_exports),'builtin_exports_exact_original_rows':True,
                'config_exact_original':True,'release_unchanged':True,'initramfs_unchanged':True,
                'module_files_written':False,'B_default_false_unchanged':True,'bootargs_changed':False,
                'dwc_sources':DWC_SOURCES,'dwc_dependency_targets':DWC_TARGETS,'pm_unwind_complete':False,
                'DTB_modules_install_packaging':False,'device_access':False,'physical_validation':False}
        save(OUT/'build-result.json',result)
        state.update(terminal=True,phase='passed',returncode=0);save(OUT/'child-state.json',state)
        event('B-build-passed',outputs=outputs,remaining_leaf_count=len(leaves)-9)
        return 0
    except BaseException as e:
        state.update(terminal=True,phase='failed',returncode=1,error=repr(e));save(OUT/'child-state.json',state)
        now=base.closure()
        save(OUT/'failure-link-input-delta.json',[{'path':n,'before':original.get(n),'after':now.get(n)} for n in sorted(original.keys()|now.keys()) if original.get(n)!=now.get(n)])
        raise

def parent():
    check_local()
    assert not sys.flags.optimize, 'Non-optimized interpreter required'
    assert os.getuid()==0 and not OUT.exists(),'Unique output exists; no replay'
    assert not (HERE/'build-result.json').exists(), 'Do not overwrite original receipt'
    frozen=json.loads((BASELEAF/'delivery.json').read_bytes())
    for n,d in frozen['files'].items():assert sha(BASELEAF/n)==d,n
    baseline=json.loads((BASELEAF/'result.json').read_bytes());assert baseline['passed']
    assert all(sha(FROZEN/Path(n).name)==h for n,h in DWC_SOURCES.items())
    assert {n:sha(BASE/'build'/n) for n in RAMFS_EXPECTED}==RAMFS_EXPECTED
    spec=importlib.util.spec_from_file_location('original_storage284',REF/'kernel284/storage.py')
    storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
    assert sha(REF/'kernel284/storage.py')=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
    assert storage.mounted_build()==BUILD
    previous=json.loads((PREVIOUS/'build-result.json').read_bytes())
    assert previous['passed'] and sha(BASE/'result.json')==sha(PREVIOUS/'build-result.json')
    assert json.loads((BASE/'namespace-process.json').read_bytes())['terminal']
    assert json.loads((BASE/'namespace-process.json').read_bytes())['returncode']==0
    assert sha(BASE/'source354'/REL)==B_SHA
    scope=json.loads((HERE.parent/'dwc-start-recovery-image-integration-plan/dependency-result.json').read_bytes())
    assert set(scope['required_object_targets'])==set(DWC_TARGETS)
    for row in scope['core_h_dependencies']:
        assert sha(BASE/'build'/row['cmd_path'])==row['cmd_sha256']
        assert sha(BASE/'build'/row['target'])==row['object_sha256']
        assert sha(BASE/'source354'/row['source_path'])==row['source_sha256']
    assert sha(BASE/'source354/drivers/usb/dwc3/core.h')=='525c1d5d8d0e501f4a92ddd6232961542b5c04521f29a50b8acf9ee86c41373c'
    assert all(sha(BASE/'build'/n)==row['sha256'] for n,row in previous['build']['outputs'].items())
    assert previous['build']['builtin_exports_exact_original_rows']
    link=json.loads((base.PLAN/'link-inputs.json').read_bytes())
    for name,row in link['toolchains'].items():
        if row['path']: assert sha(Path(row['path']).resolve())==row['sha256'], name
    for row in link['rust_toolchains']: assert sha(row['path'])==row['sha256']
    parent_ns=base.namespace();mount_before=base.mounts()
    mount_sha=hashlib.sha256(('\n'.join(mount_before)+'\n').encode()).hexdigest()
    shared_names=['.config','Module.symvers','arch/arm64/boot/Image','vmlinux','drivers/power/supply/bq27xxx_battery.o',*DWC_TARGETS]
    shared_source_names=[SOURCE/'drivers/usb/dwc3'/n for n in ['core.c','core.h','gadget.c','Makefile']]
    shared_source_before={str(p):sha(p) for p in shared_source_names}
    shared_before={n:sha(BUILD/n) for n in shared_names}
    original363_paths=[ORIGINAL363/'result.json',ORIGINAL363/'build/arch/arm64/boot/Image',ORIGINAL363/'build/vmlinux',
                  ORIGINAL363/'build/usr/initramfs_data.cpio',ORIGINAL363/'build/usr/initramfs_inc_data',
                  ORIGINAL363/'build/usr/initramfs_data.o',ORIGINAL363/'source354'/REL]
    original363_before={str(p):sha(p) for p in original363_paths}
    OUT.mkdir(parents=True)
    stamp=datetime.now(timezone.utc)
    identity={'KBUILD_BUILD_USER':'builder','KBUILD_BUILD_HOST':'samurai','KBUILD_BUILD_VERSION':'503',
              'KBUILD_BUILD_TIMESTAMP':'Tue Oct 20 03:03:47 UTC 2026',
              'timestamp_semantics':'Explicit original Image363 reproducible timestamp; not actual compile UTC',
              'actual_build_utc':stamp.isoformat(),'UTS_RELEASE':'7.3.0-rc6-rmx1931-samurai-k363+',
              'source_commit_base':base.COMMIT,'frozen_B_source_sha256':B_SHA,'default_parameter':False,
              'dwc_sources':DWC_SOURCES,'dwc_dependency_targets':DWC_TARGETS}
    save(OUT/'identity.json',identity)
    save(OUT/'execution.json',{'pid':os.getpid(),'runner_sha256':sha(__file__),'baseline_delivery_sha256':sha(BASELEAF/'delivery.json')})
    snapshots={};ret=None;parent_error=None
    try:
        for name in ['build','source354','input-initramfs363']:
            event('snapshot-and-copy-baseline',name=name)
            snapshots[name]=base.inventory(BASE/name)
            save(OUT/(name+'-baseline-before.json'),snapshots[name])
            subprocess.run(['cp','-a','--reflink=auto',str(BASE/name),str(OUT/name)],check=True)
            assert base.inventory(OUT/name)==snapshots[name]
            assert not (base.inode_set(BASE/name)&base.inode_set(OUT/name))
        (OUT/'tmp').mkdir()
        for n,h in DWC_SOURCES.items():
            (OUT/'source354'/n).write_bytes((FROZEN/Path(n).name).read_bytes())
            assert sha(OUT/'source354'/n)==h
        assert sha(OUT/'source354'/REL)==B_SHA
        source_now=base.inventory(OUT/'source354')
        source_changes=[n for n in snapshots['source354'].keys()|source_now.keys() if snapshots['source354'].get(n)!=source_now.get(n)]
        assert sorted(source_changes)==sorted(DWC_SOURCES),source_changes
        save(OUT/'source-delta.json',{n:{'before':snapshots['source354'][n],'after':source_now[n]} for n in DWC_SOURCES})
        argv=['unshare','--mount','--propagation','private',sys.executable,'-B',str(HERE/'run-503.py'),
              '--child',str(os.getpid()),parent_ns,mount_sha]
        save(OUT/'namespace-command.json',argv)
        process=subprocess.Popen(argv,cwd=OUT)
        try:
            save(OUT/'namespace-process.json',{'pid':process.pid,'argv':argv,'terminal':False})
            event('B-namespace-child-started',child_pid=process.pid,identity=identity)
        finally:
            ret=process.wait()
        save(OUT/'namespace-process.json',{'pid':process.pid,'argv':argv,'terminal':True,'returncode':ret})
    except BaseException as e:
        parent_error=repr(e)
        raise
    finally:
        preserved={}
        event('verify-baseline-and-parent-preserved',child_returncode=ret)
        for name in snapshots:
            after=base.inventory(BASE/name)
            save(OUT/(name+'-baseline-after.json'),after)
            preserved[name]=after==snapshots[name]
        parent_mounts_unchanged=base.mounts()==mount_before
        shared_after={n:sha(BUILD/n) for n in shared_names}
        shared_source_after={str(p):sha(p) for p in shared_source_names}
        original363_after={str(p):sha(p) for p in original363_paths}
        result={'passed':parent_error is None and ret==0 and all(preserved.values()) and parent_mounts_unchanged and shared_before==shared_after and shared_source_before==shared_source_after and original363_before==original363_after,
                'private_output':str(OUT),'child_returncode':ret,'parent_error':parent_error,'baseline_trees_preserved':preserved,
                'parent_mounts_unchanged':parent_mounts_unchanged,'parent_namespace_unchanged':base.namespace()==parent_ns,
                'shared_before':shared_before,'shared_after':shared_after,'shared_critical_inputs_unchanged':shared_before==shared_after,
                'shared_source_before':shared_source_before,'shared_source_after':shared_source_after,
                'shared_sources_unchanged':shared_source_before==shared_source_after,
                'original363_before':original363_before,'original363_after':original363_after,'original363_preserved':original363_before==original363_after,
                'B_source_sha256':B_SHA,'identity':identity,'device_access':False,'SDK_access':False,
                'new_boot_or_modules_or_DTB':False}
        if (OUT/'build-result.json').is_file(): result['build']=json.loads((OUT/'build-result.json').read_bytes())
        if (OUT/'child-state.json').is_file(): result['child_state']=json.loads((OUT/'child-state.json').read_bytes())
        save(OUT/'result.json',result);save(HERE/'build-result.json',result)
        event('B-finished',passed=result['passed'],child_returncode=ret,baseline_preserved=preserved,parent_mounts_unchanged=parent_mounts_unchanged)
    return 0 if result['passed'] else 1

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':raise SystemExit(child(*sys.argv[2:]))
    if not sys.argv[1:] or sys.argv[1:]==['--check-local']:
        check_local(); print(json.dumps({'passed':True,'mode':'check-local','storage_or_build_invoked':False})); raise SystemExit(0)
    assert sys.argv[1:]==['--execute-503'],'Explicit --execute-503 required'
    raise SystemExit(parent())
