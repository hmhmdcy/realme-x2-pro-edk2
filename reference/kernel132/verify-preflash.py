from pathlib import Path
import hashlib,json,shutil,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel132';out=Path('/mnt/e/edk2-samurai-out/kernel132')
def load(path):
 with tarfile.open(path) as tf:
  data={}
  for m in tf:
   assert not m.issym() and not m.islnk() and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
   if m.isfile():
    name=m.name.removeprefix('./');assert name not in data;data[name]=tf.extractfile(m).read()
 for line in data['SHA256SUMS'].decode().splitlines():
  sha,name=line.split(None,1);assert hashlib.sha256(data[name.strip().removeprefix('./')]).hexdigest()==sha
 return data
current=load(out/'preflash-private.tar.gz');old=load(out.parent/'kernel112/layout-after.tar')
for dev in ['sda','sdb','sdc','sdd','sde','sdf']:
 for suffix in ['geometry','head','tail']:assert current[dev+'.'+suffix]==old[dev+'.'+suffix]
assert b'7.3.0-rc6-rmx1931-samurai-k129+' in current['uname.txt'] and b'#129 SMP' in current['uname.txt']
assert current['state.txt'].splitlines()[-1]==b'0' and current['phosh.txt'].strip() and current['phoc.txt'].strip()
assert current['boot-id-private.txt'].strip()==(out.parent/'kernel130/embedded-boot-id-private.txt').read_bytes().strip()
assert current['traces.txt'].splitlines() in [ [b'0',b'0'], [b'0',b'1'], [b'1',b'0'], [b'1',b'1'] ]
assert current['connector.txt']==b'connected\n'
assert current['sensors.txt']==b'offline\nvdd=0 vddio=0\n' and current['pcm.txt']==b'closed\nclosed\n'
assert current['amps.txt'].count(b'powered=0 muted=1')==2 and b'failed=1' not in current['amps.txt']
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert current[name].count(b': OK')==count and b'FAILED' not in current[name]
assert current['old129-module-check.txt'].count(b': OK')>=770 and b'FAILED' not in current['old129-module-check.txt']
assert current['old126-module-check.txt'].count(b': OK')>=770 and b'FAILED' not in current['old126-module-check.txt']
assert current['old118-ipa.sha256'].split()[0]==b'bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
assert current['bluetooth-script.sha256'].split()[0]==b'104159825484fafc3ab5cacac368a9b7a8a38bc209c509207e73d1be00102319'
parts={path:digest for digest,path in (line.split('  ',1) for line in current['partition-check.sha256'].decode().splitlines())}
expected={'/dev/sde11':'d85f110275758c981691daf0d189a50c4ae45e718da4b947085ca624c6b653f8','/dev/sde32':'daa2bd1b1ccf0aacc375543b7cf980994110a25f00a40b74a6499d7edfcb85e3','/dev/sda2':'7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'}
assert parts==expected
for filename,dev in [('boot-partition-before-private.img','/dev/sde11'),('logdump-k129-console-node.img','/dev/sde32')]:
 source=out.parent/'kernel129'/filename;assert hashlib.sha256(source.read_bytes()).hexdigest()==parts[dev]
 dest=out/('boot-partition-before-private.img' if dev=='/dev/sde11' else 'logdump-before-private.img')
 assert not dest.exists();shutil.copyfile(source,dest);assert hashlib.sha256(dest.read_bytes()).hexdigest()==parts[dev]
(out/'source-boot-id-private.txt').write_bytes(current['boot-id-private.txt'])
(out/'live-before-fdt-private.dtb').write_bytes(current['live-fdt-private.dtb'])
report=dict(preflash_audit_pass=True,current_kernel=129,target_kernel=132,current_boot_identity_verified=True,
 gpt18_unchanged=True,nv6_source4_vendor1_preserved=True,persist_unchanged=True,live_backups_match=True,
 old118_and126_and129_modules_preserved=True,bluetooth_release_path_preserved=True,gui_running_audio_idle=True,
 initial_trace_states=[int(v) for v in current['traces.txt'].splitlines()],traces_must_be_stopped_before_freeze=True,
 before_boot_sha256=parts['/dev/sde11'],before_logdump_sha256=parts['/dev/sde32'],
 archive_sha256=hashlib.sha256((out/'preflash-private.tar.gz').read_bytes()).hexdigest(),flash_partitions=['boot','logdump'],goal_complete=False)
(ref/'preflash-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'preflash-validation.json').write_text(json.dumps(dict(report,boot_id=current['boot-id-private.txt'].decode().strip()),indent=2)+'\n')
print('K132_CURRENT129_GPT18_11_SOURCES_STABLE_BOOT_LOGDUMP_ROLLBACK_PREFLASH_PASS',flush=True)
