"""Build trusted native r3 packages, preserving unrelated current payloads."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,tarfile
import host
R=Path(__file__).parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-packages-final-v4';assert not W.exists();W.mkdir(mode=0o700)
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=SDK/'etc/apk/keys';signing=json.loads((P.parent/'kernel203/signing-locations-private.json').read_text())
core=json.loads((R/'mapped-region-core-build-validation.json').read_text());gst=json.loads((R/'retained-busy-v4-build-validation.json').read_text());spa=json.loads((R/'fresh-allocation-build-validation.json').read_text())
specs=[('pipewire-libs','1.6.9-r2',P.parent/'kernel264','usr/lib/libpipewire-0.3.so.0.1609.0',P/'libpipewire-map-lookup.so',core['core_sha256'],'870b7077747b14c74f15856a20f6ab93d68fde60703e0c116e2a9a38a8f91416'),('pipewire-spa-libcamera','1.6.9-r2',P.parent/'kernel264','usr/lib/spa-0.2/libcamera/libspa-libcamera.so',P/'libspa-libcamera-fresh-allocation.so',spa['spa_sha256'],'0c3471e63587b6e930d712c8962464d636e18f2e36925ce85bb91f7349e8a9a8'),('gst-plugin-pipewire','1.6.9-r1',P.parent/'kernel262','usr/lib/gstreamer-1.0/libgstpipewire.so',P/'libgstpipewire-retained-busy-v4.so',gst['plugin_sha256'],'d7a5500688d2881d04bc04c614eb46f00da7070bb96224c7f43f97b3a0e22935')]
def run(args,label):
 q=subprocess.run([str(x) for x in args],capture_output=True);(P/(label+'-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,label;return q
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def symbols(p,label):
 q=run(['aarch64-linux-gnu-readelf','--dyn-syms','--wide',p],label);out={}
 for line in q.stdout.decode().splitlines():
  a=line.split()
  if len(a)>=8 and a[4] in ['GLOBAL','WEAK','UNIQUE'] and a[6]!='UND':out[a[7].split('@')[0]]=dict(type=a[3],bind=a[4])
 return out

def metadata(base,label):
 if base.read_bytes()[:2]==b'\x1f\x8b':
  with tarfile.open(base,'r:gz',ignore_zeros=True) as a:
   out={}
   for line in a.extractfile('.PKGINFO').read().decode().splitlines():
    if ' = ' in line:k,v=line.split(' = ',1);out.setdefault(k,[]).append(v)
   return out
 # Current project packages use APK3 ADB metadata, not gzip control tarballs.
 text=run([apk,'--keys-dir',keys,'adbdump',base],label+'-r3-control').stdout.decode()
 out={};inside=False;current=None
 rename={'name':'pkgname','version':'pkgver','description':'pkgdesc','depends':'depend','install-if':'install_if'}
 for line in text.splitlines():
  if line=='info:':inside=True;continue
  if not inside:continue
  if line and not line.startswith(' '):break
  m=re.match(r'^  ([a-z][a-z_-]*):(?: (.*))?$',line)
  if m:
   current=rename.get(m[1],m[1]);value=m[2] or ''
   out[current]=[] if not value or value.startswith('#') else [value]
  elif line.startswith('    - ') and current:out[current].append(line[6:])
 assert out.get('pkgname') and out.get('pkgver') and out.get('depend'),out.keys()
 return out

report=[]
for name,version,parent,relative,binary,expected,original in specs:
 base=parent/(name+'-'+version+'.apk');run([apk,'--keys-dir',keys,'verify',base],name+'-r3-base-verify');shutil.copyfile(base,P/base.name)
 fields=metadata(base,name)
 assert fields['pkgver']==[version]
 payload=W/name;payload.mkdir()
 if base.read_bytes()[:2]==b'\x1f\x8b':
  run([apk,'--keys-dir',keys,'extract','--destination',payload,base],name+'-r3-extract')
 else:
  # The APK3 extractor rejects shared ancestors absent from its package
  # directory table. Reconstruct the current payload from its trusted
  # upstream APK and exact current binary, then require every regular file
  # to match the SHA256 manifest of the signed current APK3.
  upstream=(P.parent/'kernel262/source/gst-plugin-pipewire-1.6.9-r0.apk') if name=='gst-plugin-pipewire' else P.parent/'kernel264'/(name+'-1.6.9-r0.apk')
  previous_binary={'pipewire-libs':P.parent/'kernel264/libpipewire-binding-reset.so','pipewire-spa-libcamera':P.parent/'kernel264/libspa-libcamera-reset-output.so','gst-plugin-pipewire':P.parent/'kernel262/libgstpipewire-profile.so'}[name]
  assert sha(previous_binary)==original
  run([apk,'--keys-dir',keys,'verify',upstream],name+'-trusted-upstream-verify')
  run([apk,'--keys-dir',keys,'extract','--destination',payload,upstream],name+'-trusted-upstream-extract')
  shutil.copyfile(previous_binary,payload/relative)
  signed_manifest={};directory=None;filename=None
  for line in (P/(name+'-r3-control-private.log')).read_text().splitlines():
   m=re.match(r'^  - name: (.+)$',line)
   if m:directory=m[1];filename=None;continue
   m=re.match(r'^      - name: (.+)$',line)
   if m:filename=m[1];continue
   m=re.match(r'^        hash: ([0-9a-f]{64})$',line)
   if m:assert directory and filename;signed_manifest[directory+'/'+filename]=m[1]
  reconstructed={str(p.relative_to(payload)):sha(p) for p in payload.rglob('*') if p.is_file() and not p.is_symlink()}
  assert signed_manifest and reconstructed==signed_manifest,(name,set(reconstructed)^set(signed_manifest))
 manifest={str(p.relative_to(payload)):sha(p) for p in payload.rglob('*') if p.is_file() and not p.is_symlink()}
 links={str(p.relative_to(payload)):os.readlink(p) for p in payload.rglob('*') if p.is_symlink()}
 assert manifest[relative]==original
 old=symbols(payload/relative,name+'-r3-original-symbols')
 if binary:assert sha(binary)==expected;shutil.copyfile(binary,payload/relative);(payload/relative).chmod(0o755)
 assert sha(payload/relative)==expected
 new=symbols(payload/relative,name+'-r3-candidate-symbols');assert set(old)<=set(new),sorted(set(old)-set(new))
 changed=[rel for rel,digest in manifest.items() if sha(payload/rel)!=digest];assert changed==([relative] if binary else [])
 assert all((payload/rel).is_symlink() and os.readlink(payload/rel)==target for rel,target in links.items())
 depends=[d for d in fields['depend'] if not d.startswith('pipewire-libs=')]
 if name in ['pipewire-spa-libcamera','gst-plugin-pipewire']:depends.append('pipewire-libs=1.6.9-r3')
 epoch=1792281600
 for p in [*payload.rglob('*'),payload]:os.chown(p,0,0);os.utime(p,(epoch,epoch),follow_symlinks=False)
 meta=dict(name=name,version='1.6.9-r3',arch='aarch64',origin='pipewire',description=fields['pkgdesc'][0],url=fields['url'][0],license=fields['license'][0],depends=' '.join(depends),**{'build-time':str(epoch),'maintainer':'Realme X2 Pro Linux port'})
 if fields.get('provides'):meta['provides']=' '.join(fields['provides'])
 if fields.get('install_if'):meta['install-if']=' '.join(x.replace('1.6.9-r0','1.6.9-r3').replace('1.6.9-r1','1.6.9-r3').replace('1.6.9-r2','1.6.9-r3') for x in fields['install_if'])
 if fields.get('replaces'):meta['replaces']=' '.join(fields['replaces'])
 output=P/(name+'-1.6.9-r3.apk');assert not output.exists()
 args=[apk,'mkpkg','--compat','3.0.0','--compression','deflate:9','--files',payload,'--sign-key',signing['private_key'],'--output',output]
 for k,v in sorted(meta.items()):args+=['--info',k+':'+v]
 run(args,name+'-r3-package-build');run([apk,'--keys-dir',keys,'verify',output],name+'-r3-verify')
 report.append(dict(package=name,version='1.6.9-r3',original_version=version,apk_sha256=sha(output),original_apk_sha256=sha(base),changed_payload=relative,payload_sha256=expected,original_payload_sha256=original,actually_changed_payload_files=changed,other_regular_files_unchanged=len(manifest)-len(changed),symlinks_preserved=len(links),current_and_candidate_signatures_verified=True,abi_symbols_removed=[],extra_exports=sorted(set(new)-set(old)),depends=depends,phone_not_modified=True))
(R/'package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

