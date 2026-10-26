"""Make a signed APK retaining the verified upstream package metadata."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tarfile
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel262')
W=Path('/home/cy122/x2pro-linux/libcamera214-root/work/pipewire262/package-r2')
assert not W.exists();W.mkdir(mode=0o700)
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
signing=json.loads((P.parent/'kernel203/signing-locations-private.json').read_text())
trusted=Path('/home/cy122/x2pro-linux/libcamera214-root/etc/apk/keys')
base=P/'source/gst-plugin-pipewire-1.6.9-r0.apk'
def run(args,label):
 q=subprocess.run([str(x) for x in args],capture_output=True)
 (P/(label+'-private.log')).write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,label
 return q
run([apk,'--keys-dir',trusted,'verify',base],'package-base-verify')
with tarfile.open(base,'r:gz',ignore_zeros=True) as a:
 fields={}
 for line in a.extractfile('.PKGINFO').read().decode().splitlines():
  if ' = ' in line:
   k,v=line.split(' = ',1);fields.setdefault(k,[]).append(v)
 expected=[m.name for m in a.getmembers() if m.isfile() and not m.name.startswith('.')]
 assert expected==['usr/lib/gstreamer-1.0/libgstpipewire.so']
payload=W/'payload';payload.mkdir()
run([apk,'--keys-dir',trusted,'extract','--destination',payload,base],'package-base-extract')
binary=payload/expected[0];basehash=hashlib.sha256(binary.read_bytes()).hexdigest()
proof=json.loads((R/'profile-build-validation.json').read_text())
candidate=P/'libgstpipewire-profile.so'
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==proof['candidate_sha256']
shutil.copyfile(candidate,binary);binary.chmod(0o755)
epoch=1792281600
for p in [*payload.rglob('*'),payload]:os.chown(p,0,0);os.utime(p,(epoch,epoch),follow_symlinks=False)
meta=dict(name='gst-plugin-pipewire',version='1.6.9-r1',arch='aarch64',origin='pipewire',description=fields['pkgdesc'][0],url=fields['url'][0],license=fields['license'][0],depends=' '.join(fields['depend']),**{'install-if':' '.join(fields['install_if']),'build-time':str(epoch),'maintainer':'Realme X2 Pro Linux port'})
output=P/'gst-plugin-pipewire-1.6.9-r1.apk';assert not output.exists()
args=[apk,'mkpkg','--compat','3.0.0','--compression','deflate:9','--files',payload,'--sign-key',signing['private_key'],'--output',output]
for k,v in sorted(meta.items()):args+=['--info',k+':'+v]
run(args,'package-build')
run([apk,'--keys-dir',trusted,'verify',output],'package-local-verify')
report=dict(stage=262,package='gst-plugin-pipewire',version='1.6.9-r1',base_package='1.6.9-r0',base_apk_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),base_plugin_sha256=basehash,plugin_sha256=proof['candidate_sha256'],apk_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),signed=True,upstream_signature_verified=True,upstream_dependencies_install_if_preserved=True,changed_payload_files=expected,phone_not_modified_by_package_build=True)
(R/'package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
