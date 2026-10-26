from pathlib import Path
import tarfile,json,hashlib,shutil,struct,ast
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
 with tarfile.open(path) as tf:
  data={}
  for m in tf:
   assert not m.issym() and not m.islnk()
   if not m.isfile():continue
   name=m.name.removeprefix('./');assert name not in data and '..' not in Path(name).parts and not Path(name).is_absolute();data[name]=tf.extractfile(m).read()
 for line in data['SHA256SUMS'].decode().splitlines():
  digest,name=line.split('  ',1);assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
 return data
current=load(out/'preflash-private.tar');old=load(out.parent/'kernel112/layout-after.tar')
for dev in ['sda','sdb','sdc','sdd','sde','sdf']:
 for suffix in ['geometry','head','tail']:assert current[dev+'.'+suffix]==old[dev+'.'+suffix]
assert b'#118 SMP PREEMPT' in current['uname.txt'] and current['state.txt'].splitlines()[-1]==b'0'
assert current['boot-id-private.txt'].strip()==(out.parent/'kernel119/current-boot-id-private.txt').read_bytes().strip()
assert current['phosh.txt'].strip()==b'3492' and current['phoc.txt'].strip()==b'3190' and current['connector.txt'].strip()==b'connected'
assert all(line in [b'0',b'ABSENT'] for line in current['traces.txt'].splitlines())
assert current['sensors.txt'].strip()==b'offline\nvdd=0 vddio=0' and current['pcm.txt'].strip()==b'closed\nclosed' and current['amps.txt'].count(b'powered=0 muted=1')==2
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert current[name].count(b': OK')==count and b'FAILED' not in current[name]
assert current['ipa-module.sha256'].split()[0]==b'bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
parts={path:digest for digest,path in (line.split('  ',1) for line in current['partition-check.sha256'].decode().splitlines())}
assert parts['/dev/sde11']=='e9863902b2e9cd0cb02257f87d868989d69f613c66fbca3b6a7158a86b9c336f' and parts['/dev/sde32']=='14cdd1c47d43afe302cb1557de9573f2b96b2816c01116cb2bb5b465d68373a9' and parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
for source,name,dev in [(out.parent/'kernel115/boot-partition-k115.img','boot-partition-before-private.img','/dev/sde11'),(out.parent/'kernel118/logdump-k118-ctl-final-read.img','logdump-before-private.img','/dev/sde32')]:
 assert sha(source)==parts[dev];dest=out/name
 if not dest.exists():shutil.copyfile(source,dest)
 assert sha(dest)==parts[dev]
source=(ref/'record-build-and-modules.py').read_text();function=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='executable_sections');scope={'struct':struct};exec(ast.get_source_segment(source,function),scope);sections=scope['executable_sections']
with tarfile.open(out/'modules-k126-private.tar.gz') as tf:new={Path(m.name).stem:tf.extractfile(m).read() for m in tf if m.isfile() and m.name.endswith('.ko') and '/drivers/bluetooth/' in m.name}
for module in ['btqca','btbcm','hci_uart']:
 for prefix in ['legacy','current']:assert sections(current['bluetooth-modules-before/'+prefix+'-'+module+'.ko'])==sections(new[module]),module
(out/'source-boot-id-private.txt').write_bytes(current['boot-id-private.txt']);(out/'bluetooth-script-before-private').write_bytes(current['bluetooth-script-before'])
report=dict(preflash_audit_pass=True,current_kernel=118,target_kernel=126,same_current_boot=True,taint=0,gpt18_unchanged=True,nv6_source4_vendor1_preserved=True,persist_unchanged=True,current_gui_and_audio_idle_verified=True,ipa_fixed_module_preserved=True,live_backups_match=True,before_boot_sha256=parts['/dev/sde11'],before_logdump_sha256=parts['/dev/sde32'],before_bluetooth_script_sha256=hashlib.sha256(current['bluetooth-script-before']).hexdigest(),legacy_and_current_bluetooth_executable_sections_match126=True,archive_sha256=sha(out/'preflash-private.tar'),old_modules_not_replaced=True,flash_partitions=['logdump'],goal_complete=False)
(ref/'preflash-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'preflash-validation.json').write_text(json.dumps(dict(report,boot_id=current['boot-id-private.txt'].decode().strip()),indent=2)+'\n');print('K126_FRESH118_GPT18_11_SOURCE_PERSIST_BACKUP_AND_BT_ABI_PREFLASH_PASS')
