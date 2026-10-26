"""Build paired native packages without changing production or unrelated payloads."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,tarfile
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel264');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire264-packages';assert not W.exists();W.mkdir(mode=0o700)
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=SDK/'etc/apk/keys';signing=json.loads((P.parent/'kernel203/signing-locations-private.json').read_text());proof=json.loads((R/'binding-reset-build-validation.json').read_text());inputs=json.loads((R.parent/'kernel263/common-package-inputs-validation.json').read_text())
def run(args,label):
 q=subprocess.run([str(x) for x in args],capture_output=True);(P/(label+'-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,label;return q
def symbols(p,label):
 s=run(['aarch64-linux-gnu-readelf','--dyn-syms','--wide',p],label).stdout.decode();out={}
 for line in s.splitlines():
  a=line.split()
  if len(a)>=8 and a[4] in ['GLOBAL','WEAK','UNIQUE'] and a[6]!='UND':out[a[7].split('@')[0]]=dict(type=a[3],bind=a[4])
 return out
report=[]
specs=[('pipewire-libs','usr/lib/libpipewire-0.3.so.0.1609.0','libpipewire-binding-reset.so','core_sha256'),('pipewire-spa-libcamera','usr/lib/spa-0.2/libcamera/libspa-libcamera.so','libspa-libcamera-reset-output.so','spa_sha256')]
for name,relative,candidate,key in specs:
 base=P.parent/'kernel263'/(name+'-1.6.9-r0.apk');assert hashlib.sha256(base.read_bytes()).hexdigest()==next(i['apk_sha256'] for i in inputs if name+'-1.6.9-r0' in i['owner'])
 shutil.copyfile(base,P/base.name);run([apk,'--keys-dir',keys,'verify',base],name+'-base-verify')
 with tarfile.open(base,'r:gz',ignore_zeros=True) as a:
  fields={}
  for line in a.extractfile('.PKGINFO').read().decode().splitlines():
   if ' = ' in line:k,v=line.split(' = ',1);fields.setdefault(k,[]).append(v)
 payload=W/name;payload.mkdir();run([apk,'--keys-dir',keys,'extract','--destination',payload,base],name+'-extract')
 manifest={str(p.relative_to(payload)):hashlib.sha256(p.read_bytes()).hexdigest() for p in payload.rglob('*') if p.is_file() and not p.is_symlink()}
 symlinks={str(p.relative_to(payload)):os.readlink(p) for p in payload.rglob('*') if p.is_symlink()}
 before=manifest[relative];assert before==next(i['sha256'] for i in inputs if i['path']=='/'+relative)
 binary=P/candidate;assert hashlib.sha256(binary.read_bytes()).hexdigest()==proof[key]
 old=symbols(payload/relative,name+'-original-symbols');new=symbols(binary,name+'-candidate-symbols');missing={k:old[k] for k in sorted(set(old)-set(new))}
 if name=='pipewire-libs':assert not missing,missing
 else:
  # SPA's public module entry remains identical. GCC's allocator RTTI object
  # is incidental C++ implementation output, not a SPA factory ABI entry.
  assert set(missing)<= {'_ZTISt19_Sp_make_shared_tag'},missing
  assert all(v['type']=='OBJECT' for v in missing.values())
  assert 'spa_handle_factory_enum' in old and 'spa_handle_factory_enum' in new
  assert not [k for k,v in old.items() if v['type']=='FUNC' and k not in new]
 shutil.copyfile(binary,payload/relative);(payload/relative).chmod(0o755)
 changed=[rel for rel,digest in manifest.items() if hashlib.sha256((payload/rel).read_bytes()).hexdigest()!=digest];assert changed==[relative]
 assert all((payload/rel).is_symlink() and os.readlink(payload/rel)==target for rel,target in symlinks.items())
 epoch=1792281600
 for p in [*payload.rglob('*'),payload]:os.chown(p,0,0);os.utime(p,(epoch,epoch),follow_symlinks=False)
 depends=list(fields['depend'])
 if name=='pipewire-spa-libcamera':depends.append('pipewire-libs=1.6.9-r2')
 meta=dict(name=name,version='1.6.9-r2',arch='aarch64',origin='pipewire',description=fields['pkgdesc'][0],url=fields['url'][0],license=fields['license'][0],depends=' '.join(depends),**{'build-time':str(epoch),'maintainer':'Realme X2 Pro Linux port'})
 if fields.get('provides'):meta['provides']=' '.join(fields['provides'])
 if fields.get('install_if'):meta['install-if']=' '.join(fields['install_if'])
 output=P/(name+'-1.6.9-r2.apk');assert not output.exists()
 args=[apk,'mkpkg','--compat','3.0.0','--compression','deflate:9','--files',payload,'--sign-key',signing['private_key'],'--output',output]
 for k,v in sorted(meta.items()):args+=['--info',k+':'+v]
 run(args,name+'-package-build');run([apk,'--keys-dir',keys,'verify',output],name+'-candidate-verify')
 report.append(dict(package=name,version='1.6.9-r2',apk_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),changed_payload=relative,payload_sha256=proof[key],original_payload_sha256=before,other_regular_files_unchanged=len(manifest)-1,symlinks_preserved=len(symlinks),original_signature_verified=True,candidate_signature_verified=True,missing_incidental_cpp_objects=missing,public_factory_and_function_exports_preserved=True,upstream_dependencies_provides_preserved=True,extra_dependencies=[x for x in depends if x not in fields['depend']],phone_not_modified=True))
(R/'package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
