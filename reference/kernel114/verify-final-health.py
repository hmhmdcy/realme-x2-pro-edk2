from pathlib import Path
import hashlib, json, re, tarfile

private=Path('/mnt/e/edk2-samurai-out/kernel114')
def read_archive(path):
    with tarfile.open(path) as tar:
        files={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256(files[name.removeprefix('./')]).hexdigest()==digest
    return files
assert hashlib.sha256((private/'final-health-private.tar.gz').read_bytes()).hexdigest()=='b15c919656869f4c76638365c7c2437d57aa7721b9dfdd7b6bea6505fd23d5f5'
files=read_archive(private/'final-health-private.tar.gz')
baseline=read_archive(private/'live-userspace-private.tar.gz')
count=lambda data,p:len(re.findall(p,data.decode(),re.I))
checks=dict(kernel_113=files['uname.txt'].decode().startswith('#113 '),
            same_boot=files['boot-id-private.txt']==baseline['boot-id-private.txt'],taint_unchanged=int(files['taint.txt'])==512,
            sensor_power_off=files['sensor.txt'].decode().strip()=='offline\nvdd=0 vddio=0',
            pcm_closed=files['pcm.txt'].decode().strip()=='closed\nclosed',
            both_amps_idle=files['amps.txt'].decode().count('powered=0 muted=1')==2,
            phosh_phoc_running=bool(files['phosh.txt'].strip()) and bool(files['phoc.txt'].strip()),
            traces_off=all(line.endswith(' 0') for line in files['traces.txt'].decode().splitlines()),
            nv6_source4_unchanged=files['nv-check.txt'].decode().count(': OK')==6 and files['source-check.txt'].decode().count(': OK')==4,
            no_new_dpu_timeouts=count(files['dmesg.txt'],'frame done timeout')==count(baseline['dmesg-before.txt'],'frame done timeout'),
            no_new_gpu_faults=count(files['dmesg.txt'],'gpu fault')==count(baseline['dmesg-before.txt'],'gpu fault'))
assert all(checks.values()),checks
report=dict(all_archive_member_hashes_verified=True,checks=checks,
            diagnostics_drained=True,new_kernel_not_deployed=True,new_image_not_flashed=True,
            live_packages_updated=True,hardware_complete=False,goal_complete=False)
public=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114')
(public/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
reports={p.stem:json.loads(p.read_text()) for p in public.glob('*-validation.json') if p.name!='checkpoint-validation.json'}
(public/'checkpoint-validation.json').write_text(json.dumps(dict(stage=114,evidence=reports,goal_complete=False),indent=2)+'\n')
print(json.dumps(report,indent=2))
