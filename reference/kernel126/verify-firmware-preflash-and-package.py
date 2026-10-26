from pathlib import Path
import tarfile,hashlib,json,ast
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126')
source=(ref/'verify-preflash.py').read_text();node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='load');scope={'tarfile':tarfile,'Path':Path,'hashlib':hashlib};exec(ast.get_source_segment(source,node),scope);load=scope['load']
current=load(out/'firmware-preflash-private.tar');old=load(out.parent/'kernel112/layout-after.tar')
for dev in ['sda','sdb','sdc','sdd','sde','sdf']:
 for suffix in ['geometry','head','tail']:assert current[dev+'.'+suffix]==old[dev+'.'+suffix]
assert b'#126 SMP PREEMPT' in current['uname.txt'] and current['state.txt'].splitlines()[-1]==b'0'
assert current['boot-id-private.txt'].strip()==(out/'current-boot-id-private.txt').read_bytes().strip()
assert current['phosh.txt'].strip().isdigit() and current['phoc.txt'].strip().isdigit() and current['connector.txt'].strip()==b'connected'
assert current['amps.txt'].count(b'failed=0')==2
# A live desktop may play a notification during this read-only snapshot.
# Actual closed PCM and muted amplifiers are mandatory after GUI quiesce.
initial_audio_idle=current['pcm.txt'].strip()==b'closed\nclosed' and current['amps.txt'].count(b'powered=0 muted=1')==2
assert current['sensors.txt'].strip()==b'offline\nvdd=0 vddio=0'
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert current[name].count(b': OK')==count and b'FAILED' not in current[name]
assert current['new-module-check.txt'].count(b': OK')>=770 and b'FAILED' not in current['new-module-check.txt']
parts={n:h for h,n in (l.split('  ',1) for l in current['partition-check.sha256'].decode().splitlines())}
boot=json.loads((out/'boot-package-validation.json').read_text())
assert parts['/dev/sde11']==boot['boot_sha256'] and parts['/dev/sde32']==boot['logdump_sha256'] and parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
assert current['ipa-module.sha256'].split()[0]==b'979975a67b2af59c5487f26f1d66ab84beb8374f74db4d75740eb3a362016ad3'
fw=out/'canonical-firmware';audit=json.loads((fw/'firmware-validation.json').read_text());restore=json.loads((out/'original-firmware-restore-validation.json').read_text())
assert audit['firmware_audit_pass'] and audit['only_embedded_dtb_changed'] and audit['actual_device_boot_115_executables_preserved'] and restore['original_boot_byte_exact_restored']
raw=(fw/'boot-k126-internal-tpg.img').read_bytes();assert len(raw)==audit['boot_bytes'] and hashlib.sha256(raw).hexdigest()==audit['boot_sha256']
image=out/'boot-partition-k126-embedded-tpg.img';assert not image.exists()
baseline=(out/'boot-partition-before-private.img').read_bytes()
assert len(baseline)==100663296 and hashlib.sha256(baseline).hexdigest()==parts['/dev/sde11']
image.write_bytes(raw+baseline[len(raw):])
assert image.stat().st_size==100663296 and image.read_bytes()[:len(raw)]==raw and image.read_bytes()[len(raw):]==baseline[len(raw):]
report=dict(fresh_current126_preflash_pass=True,same_boot_identity=True,taint=0,gpt18_unchanged=True,nv6_source4_vendor1_unchanged=True,persist_unchanged=True,all770_matching_modules=True,gui_running=True,initial_audio_idle=initial_audio_idle,post_gui_pcm_and_amp_idle_required=True,boot_tail_after_payload_byte_preserved=True,only_embedded_dtb_changed=True,other_uefi_executable_bytes_unchanged=True,canonical_source_and_original_build_restored=True,before_boot_sha256=parts['/dev/sde11'],logdump_sha256=parts['/dev/sde32'],boot_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),boot_bytes=image.stat().st_size,dtb_sha256=audit['dtb_sha256'],flash_partitions=['boot'],userdata_erased=False,goal_complete=False)
(ref/'firmware-deployment-package-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'firmware-deployment-package-validation.json').write_text(json.dumps(dict(report,boot_id=current['boot-id-private.txt'].decode().strip()),indent=2)+'\n')
print(json.dumps(report))
