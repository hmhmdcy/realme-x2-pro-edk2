"""Prepare final candidate packages from tested core, SPA and Gst bytes."""
from pathlib import Path
import host
R=Path(__file__).parent
s=(R/'build-packages.py').read_text().replace("W=SDK/'work/pipewire265-packages'","W=SDK/'work/pipewire265-packages-final-v2'").replace("gst=json.loads((R/'retained-busy-v3-build-validation.json').read_text())","gst=json.loads((R/'retained-busy-v4-build-validation.json').read_text());spa=json.loads((R/'fresh-allocation-build-validation.json').read_text())").replace("P/'libgstpipewire-retained-busy-v3.so'","P/'libgstpipewire-retained-busy-v4.so'")
old="('pipewire-spa-libcamera','1.6.9-r2',P.parent/'kernel264','usr/lib/spa-0.2/libcamera/libspa-libcamera.so',None,'0c3471e63587b6e930d712c8962464d636e18f2e36925ce85bb91f7349e8a9a8',"
new="('pipewire-spa-libcamera','1.6.9-r2',P.parent/'kernel264','usr/lib/spa-0.2/libcamera/libspa-libcamera.so',P/'libspa-libcamera-fresh-allocation.so',spa['spa_sha256'],"
assert s.count(old)==1;s=s.replace(old,new)
helper=r'''
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
'''
a=s.index(" with tarfile.open(base,'r:gz'");b=s.index(" assert fields['pkgver']",a);s=s[:a]+" fields=metadata(base,name)\n"+s[b:]
s=s.replace('report=[]',helper+'\nreport=[]',1)
p=R/'build-final-packages.py'
if p.exists():(host.PRIVATE/'build-final-packages-first-generator-failure-private.py').write_bytes(p.read_bytes())
p.write_text(s)
print('Prepared APK2/APK3-aware final package builder')

