from pathlib import Path
import concurrent.futures,hashlib,json,subprocess,urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel113')
repo=out/'vendor-lineage18-reference-git-private'
dest=out/'lineage18-sensor-configs-reference-private'
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
commit='b94e26044cb95092add5dd8026fab0fdcb61433a'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==commit
prefix='proprietary/vendor/etc/sensors/'
tree=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r',commit,'--',prefix],text=True)
original=Path('/mnt/e/edk2-samurai-out/kernel111/source-files/k111-sensor-sources-readonly/sensors-vendor')
selected={'lsm6ds3c_0.json','mmc5603nj_0.json','stk3331_0.json','default_sensors.json','sns_reg_config'}
jobs=[]
for line in tree.splitlines():
    descriptor,path=line.split('\t',1)
    mode,kind,digest=descriptor.split()
    assert kind=='blob' and mode=='100644'
    relative=path.removeprefix(prefix)
    if Path(relative).name not in selected and not relative.endswith('_19781.json'): continue
    jobs.append((path,relative,digest))
assert len(jobs)==10

def fetch(job):
    path,relative,digest=job
    target=dest/relative
    if target.exists(): payload=target.read_bytes()
    else:
        url='https://raw.githubusercontent.com/cyyyss/vendor_realme_RMX1931/'+commit+'/'+path
        request=urllib.request.Request(url,headers={'User-Agent':'samurai-linux-readonly-reference'})
        with urllib.request.urlopen(request,timeout=20) as response: payload=response.read(2*1024*1024+1)
        assert len(payload)<=2*1024*1024
        assert hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()==digest
        assert not payload.startswith(b'version https://git-lfs.github.com/spec/v1'), 'LFS pointer is not configuration evidence'
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(payload)
    assert hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()==digest
    source=original/relative
    return dict(name=relative,reference_sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),
        exists_in_original=source.is_file(),byte_equal=source.is_file() and source.read_bytes()==payload,
        original_sha256=hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers: reports=list(workers.map(fetch,jobs))
report=dict(repository='https://github.com/cyyyss/vendor_realme_RMX1931',commit=commit,
    branch='lineage-18.1',files=reports,selected_files=10,git_blob_hashes_verified=True,
    equal_files=sum(x['byte_equal'] for x in reports),
    different_files=sum(x['exists_in_original'] and not x['byte_equal'] for x in reports),
    missing_in_original=sum(not x['exists_in_original'] for x in reports),
    third_party_same_model_vendor_reference=True,phone_configuration_changed=False,
    other_phone_persist_or_calibration_imported=False)
(ref/'lineage18-config-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'}))
