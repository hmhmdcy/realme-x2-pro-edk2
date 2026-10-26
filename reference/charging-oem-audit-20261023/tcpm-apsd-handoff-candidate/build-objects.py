"""Six affected objects only, immutable 508 lower plus private mount namespace."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('handoff_frozen508',HERE.parent/'tcpm-usb-budget-candidate/build-image.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p,base=m.p,m.base
OUT=Path('/home/cy122/charging-management-20261023/tcpm-apsd-handoff-objects-02')
LAYERS=[m.OUT]+m.LAYERS
CHANGED=json.loads((HERE/'source.json').read_bytes())['sources']
PREFIX='drivers/usb/typec/tcpm/qcom/'
OBJECTS=[PREFIX+n+'.o' for n in ['qcom_pmic_typec','qcom_pmic_typec_port',
    'qcom_pmic_typec_pdphy','qcom_pmic_typec_pdphy_stub','qcom_pmic_typec_apsd']]
OBJECTS+=['drivers/usb/dwc3/samurai-apsd-owner.o']
EXACT=['.config','arch/arm64/boot/Image','vmlinux.symvers','modules.builtin',
       'modules.builtin.modinfo','usr/initramfs_data.cpio','drivers/power/supply/bq27xxx_battery.o']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
canon=lambda p:hashlib.sha256(Path(p).read_text().encode()).hexdigest()

def lower(name,relative):
    for layer in LAYERS:
        q=layer/(name+'-upper')/relative
        if q.exists():return q
    return m.m.BASE/name/relative

def child(parent,ns,mounts):
    assert os.geteuid()==0 and base.namespace()!=ns
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    for name,target in [('source354',base.SOURCE),('build',base.BUILD)]:
        layers=[str(x/(name+'-upper')) for x in LAYERS]+[str(m.m.BASE/name)]
        opts='lowerdir='+':'.join(layers)+',upperdir='+str(OUT/(name+'-upper'))+',workdir='+str(OUT/(name+'-work'))
        subprocess.run(['mount','-t','overlay','overlay','-o',opts,str(OUT/(name+'-merged'))],check=True)
        subprocess.run(['mount','--bind',str(OUT/(name+'-merged')),str(target)],check=True)
    subprocess.run(['mount','--bind',str(m.m.BASE/'input-initramfs363'),str(base.PAYLOAD)],check=True)
    subprocess.run(['mount','-o','remount,bind,ro',str(base.PAYLOAD)],check=True)
    subprocess.run(['mount','--bind',str(OUT/'tmp'),str(base.TEMP)],check=True)
    assert p.mount_hash(parent)==mounts
    originals={}
    for target,row in CHANGED.items():
        path=base.SOURCE/target
        if row['baseline_sha256']:
            assert canon(path)==row['baseline_normalized_sha256'],target
            originals[target]=sha(path)
        else:
            assert not path.exists(),target
            originals[target]=None
        assert sha(HERE/row['file'])==row['sha256']
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((HERE/row['file']).read_bytes())
    env=base.build_environment()
    argv=['make','-C',str(base.SOURCE),'O='+str(base.BUILD),'ARCH=arm64',
          'CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j4']+OBJECTS
    started=time.monotonic()
    with (OUT/'objects.log').open('xb') as log:
        proc=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
        p.save(OUT/'process.json',{'process':p.pid_info(proc.pid),'argv':argv})
        code=proc.wait()
    diagnostics=[s for s in (OUT/'objects.log').read_text().splitlines()
        if re.search(r'\b(warning:|error:|undefined reference)',s,re.I)]
    assert code==0 and not diagnostics,(code,diagnostics)
    for n in EXACT:assert sha(base.BUILD/n)==sha(lower('build',n)),n
    syms={}
    for path in OBJECTS:
        nm=subprocess.check_output(['aarch64-linux-gnu-nm',str(base.BUILD/path)],text=True)
        syms[path]=[s.strip() for s in nm.splitlines() if re.search(r'(samurai_apsd_tcpm_|qcom_pmic_typec_apsd_)',s)]
    helper='\n'.join(syms[PREFIX+'qcom_pmic_typec_apsd.o'])
    owner='\n'.join(syms['drivers/usb/dwc3/samurai-apsd-owner.o'])
    for n in ['samurai_apsd_tcpm_quiesce','samurai_apsd_tcpm_release']:
        assert re.search(r'\bU '+n+r'\b',helper) and re.search(r'\bT '+n+r'\b',owner),n
    for path in [PREFIX+'qcom_pmic_typec.o',PREFIX+'qcom_pmic_typec_pdphy.o']:
        assert 'qcom_pmic_typec_apsd_' in '\n'.join(syms[path]),path
    p.save(OUT/'child-result.json',{'passed':True,'returncode':code,
        'seconds':time.monotonic()-started,'objects':{n:sha(base.BUILD/n) for n in OBJECTS},
        'diagnostics':diagnostics,'symbols':syms,'unchanged_build_inputs':EXACT,
        'baseline_sources':originals,'sources':{n:sha(base.SOURCE/n) for n in CHANGED}})

def main():
    assert not OUT.exists() and not (HERE/'build-result.json').exists()
    assert json.loads((HERE/'test-result.json').read_bytes())['passed']
    p.load('handoff_object_storage',ROOT/'reference/kernel284/storage.py').mounted_build()
    free={s:os.statvfs(s).f_bavail*os.statvfs(s).f_frsize for s in ['/home/cy122','/mnt/e']}
    assert free['/home/cy122']>2*1024**3 and free['/mnt/e']>2*1024**3,free
    tracked=[lower('source354',n) for n,r in CHANGED.items() if r['baseline_sha256']]
    tracked += [lower('build',n) for n in EXACT]
    before={str(q):sha(q) for q in tracked}
    ns,mounts=base.namespace(),p.mount_hash()
    OUT.mkdir()
    for name in ['source354-upper','source354-work','source354-merged','build-upper','build-work','build-merged','tmp']:
        (OUT/name).mkdir()
    argv=['unshare','--mount','--propagation','private','--fork',sys.executable,'-B',str(HERE/'build-objects.py'),
          '--child',str(os.getpid()),ns,mounts]
    with (OUT/'owner.stdout').open('xb') as stdout,(OUT/'owner.stderr').open('xb') as stderr:
        proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr)
        p.save(OUT/'owner.json',{'process':p.pid_info(proc.pid),'argv':argv})
        code=proc.wait()
    after={str(q):sha(q) for q in tracked}
    result={'passed':code==0 and before==after and ns==base.namespace() and mounts==p.mount_hash(),
        'returncode':code,'private_output':str(OUT),'parent_inputs_unchanged':before==after,
        'parent_mounts_unchanged':mounts==p.mount_hash(),'free_bytes_before':free,
        'phone_accessed':False,'new_Image':False,'installed':False}
    if code==0:result['build']=json.loads((OUT/'child-result.json').read_bytes())
    p.save(OUT/'terminal.json',{'terminal':True,'returncode':code})
    p.save(HERE/'build-result.json',result)
    print(json.dumps(result),flush=True)
    if code:print((OUT/'owner.stderr').read_text()[-4000:])
    raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':
    if sys.argv[1:2]==['--child']:child(int(sys.argv[2]),sys.argv[3],sys.argv[4])
    else:main()
