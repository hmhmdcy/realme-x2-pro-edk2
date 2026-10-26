from pathlib import Path
import hashlib,json,subprocess

out=Path('/mnt/e/edk2-samurai-out/kernel113')
repo=out/'vendor-c38-reference-git-private'
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
commit='0ef1fc05360421845f1ae905852dbfe63b26ba68'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==commit
prefix='proprietary/vendor/etc/sensors/'
tree=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r',commit,'--',prefix],text=True)
original=Path('/mnt/e/edk2-samurai-out/kernel111/source-files/k111-sensor-sources-readonly/sensors-vendor')
reports=[]
for line in tree.splitlines():
    descriptor,path=line.split('\t',1)
    mode,kind,digest=descriptor.split()
    assert kind=='blob' and mode=='100644'
    relative=path.removeprefix(prefix)
    if not (relative.startswith('config/') and relative.endswith('.json')) and relative!='sns_reg_config': continue
    pointer=(repo/path).read_bytes()
    assert hashlib.sha1(b'blob '+str(len(pointer)).encode()+b'\0'+pointer).hexdigest()==digest
    payload=(out/'c38-sensor-configs-reference-private'/relative).read_bytes()
    proof=json.loads((ref/'c38-lfs-reference.json').read_text())
    expected=next(item for item in proof['files'] if item['name']==relative)
    assert len(payload)==expected['bytes'] and hashlib.sha256(payload).hexdigest()==expected['sha256']
    assert not payload.startswith(b'version https://git-lfs.github.com/spec/v1'), 'LFS pointer is not sensor configuration evidence'
    source=original/relative
    reports.append(dict(name=relative,reference_sha256=hashlib.sha256(payload).hexdigest(),
        exists_in_original_source=source.is_file(),
        original_sha256=(hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None),
        byte_equal=(source.is_file() and source.read_bytes()==payload)))
report=dict(repository='https://github.com/arnodorian-r/vendor_dump_RMX1931',commit=commit,
    reference_is_third_party_same_model_c38_vendor_dump=True,files=reports,
    equal_files=sum(x['byte_equal'] for x in reports),different_files=sum(x['exists_in_original_source'] and not x['byte_equal'] for x in reports),
    missing_in_original=sum(not x['exists_in_original_source'] for x in reports),
    phone_configuration_changed=False,other_phone_calibration_imported=False)
(ref/'c38-config-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'}))
