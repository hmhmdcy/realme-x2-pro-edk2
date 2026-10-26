from pathlib import Path
import hashlib,json,re,subprocess,time,host

ref=Path(__file__).resolve().parent;out=host.PRIVATE
assert (out/'reboot-request-private.json').exists()
build=json.loads((out/'build-package-validation.json').read_text())
assert build['flash_partitions']==['boot'] and build['kernel_build']==183 and build['firmware_only_dtb_changed'] and build['all_firmware_code_and_non_version_data_unchanged']
lock=json.loads((out/'deployment-lock-private.json').read_text());image=Path(lock['files']['boot_candidate']['path']);rollback=Path(lock['files']['boot270_rollback']['path'])
assert len(image.read_bytes())==100663296 and hashlib.sha256(image.read_bytes()).hexdigest()==build['boot_sha256']
assert hashlib.sha256(rollback.read_bytes()).hexdigest()==build['rollback_boot_sha256']
marker=out/'boot-flash-request-private.json';assert not marker.exists()
fb='/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
def command(args,name):
    result=subprocess.run([fb,*args],capture_output=True,timeout=50)
    path=out/(name+'-private.log');assert not path.exists();path.write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,'Fastboot operation failed; inspect private log and fresh device state'
    return (result.stdout+result.stderr).decode()

deadline=time.monotonic()+40;attempt=0
while True:
    attempt+=1;devices=command(['devices'],'fastboot-devices-'+str(attempt));observed=re.findall(r'(?m)^(\S+)\s+fastboot\s*$',devices)
    if observed or time.monotonic()>=deadline:break
    time.sleep(2)
assert len(observed)==1,'No uniquely identified current fastboot device; no flash sent'
expected=json.loads((out.parent/'kernel109/fastboot-identity.json').read_text())['serial']
assert observed[0]==expected
serial=observed[0]
assert re.search(r'product:\s*msmnile\b',command(['-s',serial,'getvar','product'],'fastboot-product'))
for part,size in [('boot',100663296),('logdump',67108864)]:
    response=command(['-s',serial,'getvar','partition-size:'+part],'fastboot-size-'+part)
    match=re.search(r'partition-size:'+part+r':\s*(0x[0-9a-fA-F]+)',response);assert match and int(match[1],16)==size
marker.write_text(json.dumps(dict(actual_serial=serial,request_count=1,partitions=['boot'],candidate_sha256=build['boot_sha256']),indent=2)+'\n')
windows_image='E:/'+str(image)[len('/mnt/e/'):]
response=command(['-s',serial,'flash','boot',windows_image],'fastboot-flash-boot')
assert re.search(r"Writing 'boot'\s+OKAY",response) and 'FAILED' not in response
report=dict(stage=273,fresh_fastboot_identity_and_geometry_verified=True,boot_flash_success=True,
    boot_sha256=build['boot_sha256'],partitions_flashed=['boot'],logdump_not_flashed=True,runtime_readback_pending=True)
(ref/'flash-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'flash-validation.json').write_text(json.dumps(report,indent=2)+'\n')
marker=out/'fastboot-reboot-request-private.json';assert not marker.exists();marker.write_text(json.dumps(dict(request_count=1,actual_serial=serial)))
command(['-s',serial,'reboot'],'fastboot-reboot')
print(json.dumps(report))
