"""Create signed native candidates, preserving every unrelated upstream payload."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,tarfile
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel263');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-package';assert not W.exists();W.mkdir(mode=0o700)
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=SDK/'etc/apk/keys';signing=json.loads((P.parent/'kernel203/signing-locations-private.json').read_text());proof=json.loads((R/'reconfigure-candidate-build-validation.json').read_text());inputs=json.loads((R/'common-package-inputs-validation.json').read_text())
def run(args,label):
 q=subprocess.run([str(x) for x in args],capture_output=True);(P/(label+'-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,label;return q
def exports(p):
 s=run(['aarch64-linux-gnu-readelf','--dyn-syms','--wide',p],p.name+'-symbols').stdout.decode()
 return sorted({a[7].split('@')[0] for line in s.splitlines() if len(a:=line.split())>=8 and a[4] in ['GLOBAL','WEAK'] and a[6]!='UND'})
report=[]
specs=[('pipewire-libs','usr/lib/libpipewire-0.3.so.0.1609.0','libpipewire-reconfigure-candidate.so','core_sha256'),('pipewire-spa-libcamera','usr/lib/spa-0.2/libcamera/libspa-libcamera.so','libspa-libcamera-broadcast-candidate.so','spa_sha256')]
for name,relative,candidate,key in specs:
 base=P/(name+'-1.6.9-r0.apk');assert hashlib.sha256(base.read_bytes()).hexdigest()==next(i['apk_sha256'] for i in inputs if name+'-1.6.9-r0' in i['owner'])
 run([apk,'--keys-dir',keys,'verify',base],name+'-base-verify')
 with tarfile.open(base,'r:gz',ignore_zeros=True) as a:
  fields={}
  for line in a.extractfile('.PKGINFO').read().decode().splitlines():
   if ' = ' in line:k,v=line.split(' = ',1);fields.setdefault(k,[]).append(v)
 payload=W/name;payload.mkdir();run([apk,'--keys-dir',keys,'extract','--destination',payload,base],name+'-extract')
 manifest={str(p.relative_to(payload)):hashlib.sha256(p.read_bytes()).hexdigest() for p in payload.rglob('*') if p.is_file() and not p.is_symlink()}
 before=manifest[relative];assert before==next(i['sha256'] for i in inputs if i['path']=='/'+relative)
 binary=P/candidate;assert hashlib.sha256(binary.read_bytes()).hexdigest()==proof[key]
 missing=sorted(set(exports(payload/relative))-set(exports(binary)));assert not missing,(name,missing)
 shutil.copyfile(binary,payload/relative);(payload/relative).chmod(0o755)
 changed=[rel for rel,digest in manifest.items() if hashlib.sha256((payload/rel).read_bytes()).hexdigest()!=digest];assert changed==[relative]
 epoch=1792288800
 for p in [*payload.rglob('*'),payload]:os.chown(p,0,0);os.utime(p,(epoch,epoch),follow_symlinks=False)
 meta=dict(name=name,version='1.6.9-r1',arch='aarch64',origin='pipewire',description=fields['pkgdesc'][0],url=fields['url'][0],license=fields['license'][0],depends=' '.join(fields['depend']),**{'build-time':str(epoch),'maintainer':'Realme X2 Pro Linux port'})
 if fields.get('provides'):meta['provides']=' '.join(fields['provides'])
 if fields.get('install_if'):meta['install-if']=' '.join(fields['install_if'])
 output=P/(name+'-1.6.9-r1.apk');assert not output.exists()
 args=[apk,'mkpkg','--compat','3.0.0','--compression','deflate:9','--files',payload,'--sign-key',signing['private_key'],'--output',output]
 for k,v in sorted(meta.items()):args+=['--info',k+':'+v]
 run(args,name+'-package-build');run([apk,'--keys-dir',keys,'verify',output],name+'-candidate-verify')
 report.append(dict(package=name,version='1.6.9-r1',apk_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),changed_payload=relative,payload_sha256=proof[key],original_payload_sha256=before,other_regular_files_unchanged=len(manifest)-1,original_signature_verified=True,candidate_signature_verified=True,missing_dynamic_exports=missing,upstream_dependencies_provides_preserved=True,phone_not_modified=True))
(R/'common-package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
