from pathlib import Path
import tarfile,hashlib,json,subprocess,sys
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel126')
with tarfile.open(out/'embedded-runtime-private.tar.gz') as tf:
 data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);assert hashlib.sha256(data[n.removeprefix('./')]).hexdigest()==h
assert b'#126 SMP PREEMPT' in data['uname.txt'] and b'7.3.0-rc6-rmx1931-samurai-k126+' in data['uname.txt']
assert data['boot-id-private.txt'].strip()!=(out/'current-boot-id-private.txt').read_bytes().strip()
(out/'embedded-boot-id-private.txt').write_bytes(data['boot-id-private.txt'])
(out/'embedded-live-fdt-private.dtb').write_bytes(data['live-fdt-private.dtb'])
subprocess.run(['dtc','-I','dtb','-O','dts','-o',str(out/'embedded-live-fdt-private.dts'),str(out/'embedded-live-fdt-private.dtb')],stderr=subprocess.DEVNULL,check=True)
for name in ['dmesg.txt','services.txt','drm-resolved.txt','connector.txt','state.txt','sensors.txt','radio-audio.txt','pcm.txt','camera-nodes.txt']:
 (out/name.replace('.txt','-embedded-runtime-private.txt')).write_bytes(data[name])
parts={n:h for h,n in (l.split('  ',1) for l in data['partition-check.sha256'].decode().splitlines())}
boot=json.loads((out/'firmware-deployment-package-validation.json').read_text())
assert parts['/dev/sde11']==boot['boot_sha256'] and parts['/dev/sde32']==boot['logdump_sha256']
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
with tarfile.open(out.parent/'kernel112/layout-after.tar') as tf: old={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for dev in ['sda','sdb','sdc','sdd','sde','sdf']:
 for suffix in ['geometry','head','tail']:assert data[dev+'.'+suffix]==old[dev+'.'+suffix]
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
assert data['ipa-module.sha256'].split()[0]==b'979975a67b2af59c5487f26f1d66ab84beb8374f74db4d75740eb3a362016ad3'
sys.path.insert(0,str(r/'reference/kernel113'))
from inspect_live_fdt import fdt
expected=fdt((out/'DTB-k126-private').read_bytes());live=fdt(data['live-fdt-private.dtb'])
assert expected.keys()==live.keys()
for name,props in expected.items():assert all(live[name].get(k)==v for k,v in props.items()),name
assert live['/soc@0/camss@acb3000']['status']==b'okay\0'
report=dict(embedded126_dtb_deployed=True,all_live_dtb_expected_nodes_and_properties_match=True,kernel_build=126,new_boot_verified=True,flash_logdump_bytes_match=True,boot_bytes_match_embedded126=True,persist_unchanged=True,gpt18_unchanged=True,nv6_source4_vendor1_unchanged=True,matching_fixed_ipa_module=True,taint=int(data['state.txt'].splitlines()[-1]),phosh_running=bool(data['phosh.txt'].strip()),phoc_running=bool(data['phoc.txt'].strip()),display_connected=data['connector.txt'].strip()==b'connected',drm_resolved=data['drm-resolved.txt'].decode().strip(),hardware_complete=False,camss_runtime_pending=True,goal_complete=False)
(r/'reference/kernel126/embedded-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
