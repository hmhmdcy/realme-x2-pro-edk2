"""Stage seven signed upgrades and an isolated runtime; retain actual r8 rollback."""
from pathlib import Path
import hashlib,host,io,json,os,shlex,shutil,subprocess,tarfile

os.umask(0o077);here=Path(__file__).resolve().parent;private=host.PRIVATE
assert json.loads((here/'r10-host-runtime-qa-validation.json').read_text())['all_five_ipa_signatures_valid']
full=private/'camera-forward-repo-r10';manifest=json.loads((full/'package-manifest.json').read_text())
names={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
selected=[p for p in manifest['packages'] if p['name'] in names];assert len(selected)==7
subset=private/'camera-selected-repo-r10';assert not subset.exists();subset.mkdir(mode=0o700)
for item in selected:shutil.copyfile(full/item['file'],subset/item['file'])
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');key=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
p=subprocess.run([str(apk),'--keys-dir',str(private.parent/'kernel214/phone-trusted-public-keys'),'mkndx','--compression','deflate:9','--sign-key',str(key),'--pkgname-spec','${name}-${version}.apk','--output',str(subset/'packages.adb'),*[str(subset/item['file']) for item in selected]],capture_output=True,timeout=60)
(private/'selected-index-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
bundle=private/'r10-candidate-bundle-private.tar.gz';assert not bundle.exists();members={}
qa=Path('/home/cy122/x2pro-linux/libcamera224-r10-qa-prefix')
with tarfile.open(bundle,'w:gz') as archive:
 def add(name,data,mode=0o600):
  info=tarfile.TarInfo(name);info.size=len(data);info.mode=mode;archive.addfile(info,io.BytesIO(data));members[name]=dict(kind='file',sha256=hashlib.sha256(data).hexdigest(),mode=mode)
 for item in selected:
  data=(subset/item['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==item['sha256'];add('forward/'+item['file'],data)
  for name,record in item['files'].items():
   if not name.startswith('usr/'):continue
   path=qa/name;member='candidate/'+name
   if record['kind']=='symlink':
    assert path.is_symlink() and os.readlink(path)==record['target'];info=tarfile.TarInfo(member);info.type=tarfile.SYMTYPE;info.linkname=record['target'];info.mode=0o777;archive.addfile(info);members[member]=record
   else:
    data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==record['sha256'];add(member,data,record['mode'])
 add('forward/packages.adb',(subset/'packages.adb').read_bytes())
 add('forward-manifest.json',json.dumps(dict(packages=selected),indent=2).encode())
 yaml=(qa/'etc/libcamera/configuration.yaml').read_bytes();assert b'dma_heap: system' in yaml and b'experimental_imx471_native_quad' not in yaml
 add('candidate/config-default/libcamera/configuration.yaml',yaml,0o644)
 assert yaml.count(b'    mode: cpu')==1
 add('candidate/config-full/libcamera/configuration.yaml',yaml.replace(b'    mode: cpu',b'    mode: cpu\n    experimental_imx471_native_quad: true'),0o644)
 add('candidate/config-isolated/libcamera/configuration.yaml',yaml.replace(b'configuration:\n',b'configuration:\n  ipa:\n    force_isolation: true\n'),0o644)
 add('bundle-manifest-private.json',json.dumps(members,indent=2).encode())
data=bundle.read_bytes();record=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),members=members)
(private/'r10-bundle-metadata-private.json').write_text(json.dumps(record,indent=2)+'\n')
code=r'''
from pathlib import Path
import hashlib,json,os
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k224-r10-package-candidates'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k224-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k224-baseline/installed-before-private.txt').read_bytes()
assert not out.exists();out.mkdir(mode=0o700);(out/'bundle-private.tar.gz').touch(mode=0o600)
print('ready')
'''
assert host.ssh('python3 -',input=code.encode(),timeout=30).stdout.strip()==b'ready'
for offset in range(0,len(data),65536):
 chunk=data[offset:offset+65536]
 code="from pathlib import Path;import hashlib,sys;p=Path('/var/lib/samurai/k224-r10-package-candidates/bundle-private.tar.gz');d=sys.stdin.buffer.read();assert len(d)=="+str(len(chunk))+" and hashlib.sha256(d).hexdigest()=="+repr(hashlib.sha256(chunk).hexdigest())+";assert p.stat().st_size=="+str(offset)+";p.open('ab').write(d)"
 host.ssh('python3 -c '+shlex.quote(code),input=chunk,timeout=30)
 (private/'r10-transfer-offset-private.txt').write_text(str(offset+len(chunk)))
 if offset//65536%20==0:print(json.dumps(dict(uploaded_bytes=offset+len(chunk),total_bytes=len(data))),flush=True)
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess,tarfile
root=Path('/var/lib/samurai');out=root/'k224-r10-package-candidates';prefix=Path('/run/samurai-camera224-r10')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k224-baseline/boot-id-private.txt').read_bytes()
data=(out/'bundle-private.tar.gz').read_bytes();assert len(data)==EXPECTED_SIZE and hashlib.sha256(data).hexdigest()==EXPECTED_HASH
assert not prefix.exists();prefix.mkdir(mode=0o755)
with tarfile.open(out/'bundle-private.tar.gz') as archive:
 manifest=json.loads(archive.extractfile('bundle-manifest-private.json').read());assert {m.name for m in archive.getmembers()}==set(manifest)|{'bundle-manifest-private.json'}
 for member in archive.getmembers():
  name=member.name;assert not name.startswith('/') and '..' not in Path(name).parts
  target=prefix/name[len('candidate/'):] if name.startswith('candidate/') else out/name
  target.parent.mkdir(parents=True,exist_ok=True,mode=0o755 if name.startswith('candidate/') else 0o700)
  if member.issym():
   assert '..' not in Path(member.linkname).parts and manifest[name]['target']==member.linkname;target.symlink_to(member.linkname)
  else:
   assert member.isfile();data=archive.extractfile(member).read()
   if name in manifest:assert hashlib.sha256(data).hexdigest()==manifest[name]['sha256']
   target.write_bytes(data);target.chmod(member.mode)
for directory in [prefix,*prefix.rglob('*')]:
 if directory.is_dir() and not directory.is_symlink():directory.chmod(0o755)
for path in sorted((out/'forward').iterdir()):
 p=subprocess.run(['apk','verify',str(path)],capture_output=True,timeout=30);(out/(path.name+'.signature-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
rollback=root/'k223-r8-package-candidates';old=json.loads((rollback/'forward-manifest.json').read_text());assert len(old['packages'])==7
count=0
for package in old['packages']:
 assert package['version']==('0.1.0-r3' if package['name'].startswith('samurai-camera-') else '99990.7.2-r8')
 apk=rollback/'forward'/package['file'];assert hashlib.sha256(apk.read_bytes()).hexdigest()==package['sha256']
 p=subprocess.run(['apk','verify',str(apk)],capture_output=True,timeout=30);(out/(apk.name+'.rollback-signature-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
 for relative,item in package['files'].items():
  path=Path('/')/relative
  if item['kind']=='symlink':assert path.is_symlink() and os.readlink(path)==item['target']
  else:assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE(path.stat().st_mode)==item['mode']
  count+=1
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k224-baseline/installed-before-private.txt').read_bytes()
report=dict(stage=224,seven_forward_apks_staged=True,all_forward_signatures_and_index_verified_on_phone=True,isolated_full_feature_runtime_staged=True,
 archive_and_members_verified=True,actual_seven_r8_rollback_apks_signatures_hashes_and_current_payloads_verified=True,rollback_payload_records=count,
 private_signing_keys_not_uploaded=True,system_camera_packages_unchanged=True)
(out/'staging-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('EXPECTED_SIZE',str(record['bytes'])).replace('EXPECTED_HASH',repr(record['sha256']))
p=host.ssh('python3 -',input=code.encode(),timeout=100);(private/'r10-staging-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'r10-staging-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
