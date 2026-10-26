from pathlib import Path
import hashlib,json,os,subprocess
ROOT=Path('/mnt/e/edk2-samurai-out/charging-oem-audit-20261023')
IMAGE=ROOT/'gauge-2719-system-extract-private-01/system.img'
INDEX=ROOT/'gauge-2719-system-name-index-private-01'
OUT=ROOT/'gauge-2719-system-files-private-01';assert not OUT.exists()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
result=json.loads((INDEX/'result-private.json').read_bytes());assert result['passed']
assert sha((INDEX/'system-name-index.json').read_bytes())==result['index_sha256']=='a02e27f10a4cee336978f77e59c1524449c7a5262dd3441351bac54ef76b1dfc'
entries={r['path']:r for r in json.loads((INDEX/'system-name-index.json').read_bytes())}
selected=['/system/system_ext/app/OppoEngineerMode/OppoEngineerMode.apk',
 '/system/system_ext/etc/sys_bad_battery_config.xml','/system/euclid/my_engineering.img',
 '/system/system_ext/lib64/vendor.oplus.hardware.charger@1.0.so','/system/build.prop']
assert all(entries[p]['kind']=='regular' and 0<entries[p]['bytes']<=30000000 for p in selected)
debugfs=Path('/usr/sbin/debugfs');assert sha(debugfs.read_bytes())=='864e1d7b445e7b5bfc831da78330dbcafc590fa82b89ea9de60b7527f989954f'
before=IMAGE.stat();assert before.st_size==4487905280
OUT.mkdir(mode=0o700);records=[]
for path in selected:
    target=OUT/(path.lstrip('/').replace('/','__')+'.bin')
    with target.open('xb') as stream:
        child=subprocess.Popen([str(debugfs),'-R','cat "'+path+'"',str(IMAGE)],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.PIPE)
        try:_,stderr=child.communicate()
        finally:child.wait()
        stream.flush();os.fsync(stream.fileno())
    (OUT/(target.name+'.stderr-private.txt')).write_bytes(stderr)
    raw=target.read_bytes();assert child.returncode==0 and len(raw)==entries[path]['bytes']
    assert stderr.decode().splitlines()==['debugfs 1.47.2 (1-Jan-2025)']
    records.append(dict(path=path,private_file=target.name,sha256=sha(raw),bytes=len(raw),child_pid=child.pid,terminal=True,returncode=child.returncode))
after=IMAGE.stat();assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
report=dict(passed=True,source_image_sha256=result['image_sha256'],files=records,image_metadata_unchanged=True,
 input_image_hash_reused_from_completed_producer=True,no_mount_or_device_or_SDK_or_Git=True,
 extracted_code_executed=False)
(OUT/'result-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
