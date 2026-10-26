from pathlib import Path
import concurrent.futures,hashlib,json,re,subprocess,urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel113')
repo=out/'vendor-c38-reference-git-private'
dest=out/'c38-sensor-configs-reference-private'
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
commit='0ef1fc05360421845f1ae905852dbfe63b26ba68'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==commit
prefix='proprietary/vendor/etc/sensors/'
tree=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r',commit,'--',prefix],text=True)
jobs=[]
for line in tree.splitlines():
    descriptor,path=line.split('\t',1)
    mode,kind,git_digest=descriptor.split()
    assert kind=='blob' and mode=='100644'
    relative=path.removeprefix(prefix)
    if not (relative.startswith('config/') and relative.endswith('.json')) and relative!='sns_reg_config': continue
    pointer=(repo/path).read_bytes()
    assert hashlib.sha1(b'blob '+str(len(pointer)).encode()+b'\0'+pointer).hexdigest()==git_digest
    match=re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (\d+)\n',pointer)
    assert match,path
    digest=match[1].decode(); size=int(match[2]); assert 0<size<2*1024*1024
    jobs.append((path,relative,digest,size))
assert 10<len(jobs)<150 and sum(job[3] for job in jobs)<10*1024*1024

def fetch(job):
    path,relative,digest,size=job
    target=dest/relative
    cached=repo/'.git/lfs/objects'/digest[:2]/digest[2:4]/digest
    if target.exists():
        payload=target.read_bytes()
    else:
        if cached.is_file():
            payload=cached.read_bytes()
        else:
            url='https://media.githubusercontent.com/media/arnodorian-r/vendor_dump_RMX1931/'+commit+'/'+path
            request=urllib.request.Request(url,headers={'User-Agent':'samurai-linux-readonly-reference'})
            with urllib.request.urlopen(request,timeout=20) as response:
                payload=response.read(size+1)
        assert len(payload)==size and hashlib.sha256(payload).hexdigest()==digest,path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(payload)
    assert len(payload)==size and hashlib.sha256(payload).hexdigest()==digest,path
    return dict(name=relative,sha256=digest,bytes=size)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
    reports=list(workers.map(fetch,jobs))
report=dict(repository='https://github.com/arnodorian-r/vendor_dump_RMX1931',commit=commit,
    files=reports,lfs_object_hashes_verified=True,total_bytes=sum(item['bytes'] for item in reports),
    reference_is_third_party_same_model_vendor_dump=True,phone_configuration_changed=False)
(ref/'c38-lfs-reference.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'}))
