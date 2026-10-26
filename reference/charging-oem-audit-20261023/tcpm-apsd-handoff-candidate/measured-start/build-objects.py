"""Only new measured helper and real PHY supplier objects; no probe/Image."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;OLD=HERE.parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('frozen_handoff_objects',OLD/'build-objects.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
base,p=previous.base,previous.p
BASE=previous.m.m.BASE
LAYERS=[previous.OUT]+previous.LAYERS
OUT=Path('/home/cy122/charging-management-20261023/tcpm-apsd-measured-start-objects-01')
ROWS=json.loads((HERE/'source.json').read_bytes())['sources']
PREFIX='drivers/usb/typec/tcpm/qcom/'
OBJECTS=[PREFIX+'qcom_pmic_typec_apsd.o',PREFIX+'qcom_pmic_typec_pdphy.o']
EXACT=['.config','arch/arm64/boot/Image','vmlinux.symvers','modules.builtin',
       'modules.builtin.modinfo','usr/initramfs_data.cpio','drivers/power/supply/bq27xxx_battery.o']
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
canon=lambda path:hashlib.sha256(Path(path).read_text().encode()).hexdigest()
def lower(name,relative):
    for layer in LAYERS:
        q=layer/(name+'-upper')/relative
        if q.exists():return q
    return BASE/name/relative

def child(parent,ns,mounts):
    assert os.geteuid()==0 and base.namespace()!=ns
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    for name,target in [('source354',base.SOURCE),('build',base.BUILD)]:
        opts='lowerdir='+':'.join([str(x/(name+'-upper')) for x in LAYERS]+[str(BASE/name)])
        opts+=',upperdir='+str(OUT/(name+'-upper'))+',workdir='+str(OUT/(name+'-work'))
        subprocess.run(['mount','-t','overlay','overlay','-o',opts,str(OUT/(name+'-merged'))],check=True)
        subprocess.run(['mount','--bind',str(OUT/(name+'-merged')),str(target)],check=True)
    subprocess.run(['mount','--bind',str(BASE/'input-initramfs363'),str(base.PAYLOAD)],check=True)
    subprocess.run(['mount','-o','remount,bind,ro',str(base.PAYLOAD)],check=True)
    subprocess.run(['mount','--bind',str(OUT/'tmp'),str(base.TEMP)],check=True)
    assert p.mount_hash(parent)==mounts
    for target,row in ROWS.items():
        path=base.SOURCE/target
        # The measured header merges shutdown's callback/contract fields and
        # the preceding handoff field. Its actual immutable lower is parent.
        if row['file']=='qcom_pmic_typec.h':
            assert sha(path)==sha(OLD/'qcom_pmic_typec.h')
        else:assert canon(path)==row['baseline_normalized_sha256'],target
        assert sha(HERE/row['file'])==row['sha256']
        path.write_bytes((HERE/row['file']).read_bytes())
    env=base.build_environment()
    argv=['make','-C',str(base.SOURCE),'O='+str(base.BUILD),'ARCH=arm64',
          'CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j2']+OBJECTS
    started=time.monotonic()
    with (OUT/'objects.log').open('xb') as log:
        proc=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
        p.save(OUT/'process.json',{'process':p.pid_info(proc.pid),'argv':argv});code=proc.wait()
    diagnostics=[s for s in (OUT/'objects.log').read_text().splitlines()
        if re.search(r'\b(warning:|error:|undefined reference)',s,re.I)]
    assert code==0 and not diagnostics,(code,diagnostics)
    for name in EXACT:assert sha(base.BUILD/name)==sha(lower('build',name)),name
    nm=subprocess.check_output(['aarch64-linux-gnu-nm',str(base.BUILD/OBJECTS[1])],text=True)
    for name in ['qcom_pmic_typec_pdphy_apsd_begin','qcom_pmic_typec_pdphy_apsd_verify','qcom_pmic_typec_pdphy_apsd_release']:
        assert re.search(r'\bT '+name+r'\b',nm),name
    assert re.search(r'\bU regulator_enable\b',nm) and re.search(r'\bU regulator_disable\b',nm)
    result={'passed':True,'returncode':code,'seconds':time.monotonic()-started,
        'objects':{n:sha(base.BUILD/n) for n in OBJECTS},'diagnostics':diagnostics,
        'real_supply_symbols':[s.strip() for s in nm.splitlines() if re.search(r'(pdphy_apsd_|regulator_(enable|disable))',s)],
        'unchanged_build_inputs':EXACT,'full_probe_integration':False}
    p.save(OUT/'child-result.json',result)

def main():
    assert not OUT.exists() and not (HERE/'build-result.json').exists()
    assert json.loads((HERE/'test-result.json').read_bytes())['passed']
    manifest=json.loads((HERE/'source.json').read_bytes())
    assert sha(OLD/'delivery.json')==manifest['frozen_parent_delivery_sha256']
    for name,pin in manifest['frozen_parent_sources'].items():assert sha(OLD/name)==pin
    p.load('measured_start_storage',ROOT/'reference/kernel284/storage.py').mounted_build()
    free={s:os.statvfs(s).f_bavail*os.statvfs(s).f_frsize for s in ['/home/cy122','/mnt/e']}
    assert min(free.values())>2*1024**3
    tracked=[lower('source354',n) for n in ROWS]+[lower('build',n) for n in EXACT]
    before={str(q):sha(q) for q in tracked};ns,mounts=base.namespace(),p.mount_hash()
    OUT.mkdir()
    for name in ['source354-upper','source354-work','source354-merged','build-upper','build-work','build-merged','tmp']:
        (OUT/name).mkdir()
    argv=['unshare','--mount','--propagation','private','--fork',sys.executable,'-B',str(HERE/'build-objects.py'),
          '--child',str(os.getpid()),ns,mounts]
    with (OUT/'owner.stdout').open('xb') as stdout,(OUT/'owner.stderr').open('xb') as stderr:
        proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr)
        p.save(OUT/'owner.json',{'process':p.pid_info(proc.pid),'argv':argv});code=proc.wait()
    after={str(q):sha(q) for q in tracked}
    result={'passed':code==0 and before==after and ns==base.namespace() and mounts==p.mount_hash(),
        'returncode':code,'private_output':str(OUT),'parent_inputs_unchanged':before==after,
        'parent_mounts_unchanged':mounts==p.mount_hash(),'free_bytes_before':free,
        'phone_accessed':False,'new_Image':False,'full_probe_integration':False}
    if code==0:result['build']=json.loads((OUT/'child-result.json').read_bytes())
    p.save(OUT/'terminal.json',{'terminal':True,'returncode':code});p.save(HERE/'build-result.json',result)
    print(json.dumps(result),flush=True)
    if code:print((OUT/'owner.stderr').read_text()[-3500:])
    raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':
    if sys.argv[1:2]==['--child']:child(int(sys.argv[2]),sys.argv[3],sys.argv[4])
    else:main()
