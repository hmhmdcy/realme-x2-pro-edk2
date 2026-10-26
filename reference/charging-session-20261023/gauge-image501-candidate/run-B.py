"""Private B501 from byte-exact Image363 baseline. No device or boot packaging."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
BASELEAF=HERE.parent/'gauge-image363-baseline'
BASE=Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01')
OUT=Path('/home/cy122/charging-management-20261023/gauge-image501-B-01')
FROZEN=REF/'charging-oem-audit-20261023/gauge-current-samurai-candidate/bq27xxx_battery.c'
REL='drivers/power/supply/bq27xxx_battery.c'
B_SHA='0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe'
spec=importlib.util.spec_from_file_location('frozen_363_baseline',BASELEAF/'run-baseline.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
assert base.sha(BASELEAF/'run-baseline.py')=='136a60e4815014b4fc1afc221f2abfcd39935440def62af081059ee1e2b58650'
sha,save,event=base.sha,base.save,base.event
BUILD,SOURCE,PAYLOAD,TEMP=base.BUILD,base.SOURCE,base.PAYLOAD,base.TEMP

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
    env.update(KBUILD_BUILD_VERSION='501',KBUILD_BUILD_TIMESTAMP=identity['KBUILD_BUILD_TIMESTAMP'])
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
            save(OUT/'child-state.json',state)
            event(name,started=True,child_pid=process.pid)
            ret=process.wait();f.flush();os.fsync(f.fileno())
        phases.append({'phase':name,'returncode':ret,'seconds':round(time.monotonic()-start,2),'log_sha256':sha(log)})
        save(OUT/'commands.json',commands);save(OUT/'phases.json',phases)
        event(name,returncode=ret,seconds=phases[-1]['seconds'])
        assert ret==0,(name,ret)
    try:
        argv=['make','-C',str(SOURCE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
              'LOCALVERSION=+','W=1','V=1','-j4']
        run('B-bq-object',argv+['drivers/power/supply/bq27xxx_battery.o'])
        run('B-image',argv+['Image'])
        after=base.closure()
        leaves=json.loads((base.PLAN/'link-inputs.json').read_bytes())['members']
        stub=json.loads((base.PLAN/'final-link-inputs.json').read_bytes())['libstub_members']
        delta=[{'path':n,'before':original.get(n),'after':after.get(n)} for n in sorted(original.keys()|after.keys()) if original.get(n)!=after.get(n)]
        leaf_delta=[r for r in delta if r['path'] in leaves]
        stub_delta=[r for r in delta if r['path'] in stub]
        save(OUT/'actual-link-input-delta.json',delta);save(OUT/'actual-leaf-delta.json',leaf_delta)
        save(OUT/'closure-final.json',after)
        assert [r['path'] for r in leaf_delta]==['drivers/power/supply/bq27xxx_battery.o']
        assert not stub_delta
        assert after['init/version-timestamp.o']!=original['init/version-timestamp.o']
        old_exports=symvers(BASE/'build/Module.symvers')
        new_exports=symvers(BUILD/'vmlinux.symvers')
        save(OUT/'builtin-exports-original.json',old_exports);save(OUT/'builtin-exports-candidate.json',new_exports)
        assert old_exports==new_exports,'Export name/class/namespace/CRC/module rows changed'
        assert (BUILD/'.config').read_bytes()==(BASE/'config363-original').read_bytes()
        assert (BUILD/'include/config/kernel.release').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k363+'
        uts=(BUILD/'include/generated/utsversion.h').read_text()
        assert '#501 SMP PREEMPT '+identity['KBUILD_BUILD_TIMESTAMP'] in uts
        assert sha(SOURCE/REL)==B_SHA
        assert base.inventory(PAYLOAD)==json.loads((BASE/'initramfs-before.json').read_bytes())
        outputs={n:{'sha256':sha(BUILD/n),'bytes':(BUILD/n).stat().st_size} for n in [
            'arch/arm64/boot/Image','vmlinux','System.map','vmlinux.symvers','drivers/power/supply/bq27xxx_battery.o','init/version-timestamp.o']}
        assert outputs['arch/arm64/boot/Image']['sha256']!=base.EXPECTED['Image']
        result={'passed':True,'identity':identity,'outputs':outputs,'source_sha256':B_SHA,
                'leaf_delta':leaf_delta,'unchanged_other_leaf_count':len(leaves)-1,'unchanged_libstub_count':len(stub),
                'builtin_export_count':len(new_exports),'builtin_exports_exact_original_rows':True,
                'config_exact_original':True,'release_unchanged':True,'initramfs_unchanged':True,
                'module_files_written':False,'B_default_false_unchanged':True,'bootargs_changed':False,
                'DTB_modules_install_packaging':False,'device_access':False,'physical_validation':False}
        save(OUT/'build-result.json',result)
        state.update(terminal=True,phase='passed',returncode=0);save(OUT/'child-state.json',state)
        event('B-build-passed',outputs=outputs,remaining_leaf_count=len(leaves)-1)
        return 0
    except BaseException as e:
        state.update(terminal=True,phase='failed',returncode=1,error=repr(e));save(OUT/'child-state.json',state)
        now=base.closure()
        save(OUT/'failure-link-input-delta.json',[{'path':n,'before':original.get(n),'after':now.get(n)} for n in sorted(original.keys()|now.keys()) if original.get(n)!=now.get(n)])
        raise

def parent():
    assert os.getuid()==0 and not OUT.exists(),'Unique output exists; no replay'
    frozen=json.loads((BASELEAF/'delivery.json').read_bytes())
    for n,d in frozen['files'].items():assert sha(BASELEAF/n)==d,n
    baseline=json.loads((BASELEAF/'result.json').read_bytes());assert baseline['passed']
    assert sha(FROZEN)==B_SHA
    spec=importlib.util.spec_from_file_location('original_storage284',REF/'kernel284/storage.py')
    storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
    assert storage.mounted_build()==BUILD
    parent_ns=base.namespace();mount_before=base.mounts()
    mount_sha=hashlib.sha256(('\n'.join(mount_before)+'\n').encode()).hexdigest()
    shared_names=['.config','Module.symvers','arch/arm64/boot/Image','vmlinux','drivers/power/supply/bq27xxx_battery.o']
    shared_before={n:sha(BUILD/n) for n in shared_names}
    OUT.mkdir(parents=True)
    stamp=datetime.now(timezone.utc)
    identity={'KBUILD_BUILD_USER':'builder','KBUILD_BUILD_HOST':'samurai','KBUILD_BUILD_VERSION':'501',
              'KBUILD_BUILD_TIMESTAMP':stamp.strftime('%a %b %d %H:%M:%S UTC %Y'),
              'utc':stamp.isoformat(),'UTS_RELEASE':'7.3.0-rc6-rmx1931-samurai-k363+',
              'source_commit_base':base.COMMIT,'frozen_B_source_sha256':B_SHA,'default_parameter':False}
    save(OUT/'identity.json',identity)
    save(OUT/'execution.json',{'pid':os.getpid(),'runner_sha256':sha(__file__),'baseline_delivery_sha256':sha(BASELEAF/'delivery.json')})
    snapshots={};ret=None
    try:
        for name in ['build','source354','input-initramfs363']:
            event('snapshot-and-copy-baseline',name=name)
            snapshots[name]=base.inventory(BASE/name)
            save(OUT/(name+'-baseline-before.json'),snapshots[name])
            subprocess.run(['cp','-a','--reflink=auto',str(BASE/name),str(OUT/name)],check=True)
            assert base.inventory(OUT/name)==snapshots[name]
            assert not (base.inode_set(BASE/name)&base.inode_set(OUT/name))
        (OUT/'tmp').mkdir()
        (OUT/'source354'/REL).write_bytes(FROZEN.read_bytes())
        assert sha(OUT/'source354'/REL)==B_SHA
        source_now=base.inventory(OUT/'source354')
        source_changes=[n for n in snapshots['source354'].keys()|source_now.keys() if snapshots['source354'].get(n)!=source_now.get(n)]
        assert source_changes==[REL],source_changes
        save(OUT/'source-delta.json',{'only_changed_file':REL,'before':snapshots['source354'][REL],
                                    'after':source_now[REL]})
        argv=['unshare','--mount','--propagation','private',sys.executable,'-B',str(HERE/'run-B.py'),
              '--child',str(os.getpid()),parent_ns,mount_sha]
        save(OUT/'namespace-command.json',argv)
        process=subprocess.Popen(argv,cwd=OUT)
        save(OUT/'namespace-process.json',{'pid':process.pid,'argv':argv,'terminal':False})
        event('B-namespace-child-started',child_pid=process.pid,identity=identity)
        ret=process.wait()
        save(OUT/'namespace-process.json',{'pid':process.pid,'argv':argv,'terminal':True,'returncode':ret})
    finally:
        preserved={}
        event('verify-baseline-and-parent-preserved',child_returncode=ret)
        for name in snapshots:
            after=base.inventory(BASE/name)
            save(OUT/(name+'-baseline-after.json'),after)
            preserved[name]=after==snapshots[name]
        parent_mounts_unchanged=base.mounts()==mount_before
        shared_after={n:sha(BUILD/n) for n in shared_names}
        result={'passed':ret==0 and all(preserved.values()) and parent_mounts_unchanged and shared_before==shared_after,
                'private_output':str(OUT),'child_returncode':ret,'baseline_trees_preserved':preserved,
                'parent_mounts_unchanged':parent_mounts_unchanged,'parent_namespace_unchanged':base.namespace()==parent_ns,
                'shared_before':shared_before,'shared_after':shared_after,'shared_critical_inputs_unchanged':shared_before==shared_after,
                'B_source_sha256':B_SHA,'identity':identity,'device_access':False,'SDK_access':False,
                'new_boot_or_modules_or_DTB':False}
        if (OUT/'build-result.json').is_file(): result['build']=json.loads((OUT/'build-result.json').read_bytes())
        if (OUT/'child-state.json').is_file(): result['child_state']=json.loads((OUT/'child-state.json').read_bytes())
        save(OUT/'result.json',result);save(HERE/'build-result.json',result)
        event('B-finished',passed=result['passed'],child_returncode=ret,baseline_preserved=preserved,parent_mounts_unchanged=parent_mounts_unchanged)
    return 0 if result['passed'] else 1

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':raise SystemExit(child(*sys.argv[2:]))
    assert sys.argv[1:]==['--execute-B'],'Explicit --execute-B required'
    raise SystemExit(parent())
