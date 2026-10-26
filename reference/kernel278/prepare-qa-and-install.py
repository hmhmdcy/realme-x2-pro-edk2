"""Prepare isolated r24 QA and a package-only update; preserve the actual276 boot guard."""
from pathlib import Path
R=Path(__file__).resolve().parent
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py','prepare-runtime-repo.py','qa-packages.py']:
 s=(R.parent/'kernel277'/name).read_text()
 for a,b in [('kernel277','kernel278'),('277-r23','278-r24'),('r23','r24'),('stage=277','stage=278'),('k277','k278'),('0.1.0-r18','0.1.0-r19')]:s=s.replace(a,b)
 for a,b in [('libcamera278-r24-built','libcamera278-r24-r2-built'),('packages278-r24','packages278-r24-r2'),('packages-config278-r24','packages-config278-r24-r2')]:s=s.replace(a,b)
 if name=='collect-forward-packages.py':
  a="assert (prefix/'etc/libcamera/configuration.yaml').read_bytes()==";i=s.index(a)
  s=s[:i]+"assert (prefix/'usr/share/libcamera/ipa/simple/s5kgw1.yaml').read_bytes()==(here/'s5kgw1.yaml').read_bytes()\n"+s[i:]
 compile(s,name,'exec');p=R/name;assert not p.exists();p.write_text(s)
s=(R.parent/'kernel277/stage-r23.py').read_text()
for a,b in [('k277-package','k278-package'),('stage=277','stage=278'),('r23','r24'),('r22','r23'),('0.1.0-r18','0.1.0-r19'),('0.1.0-r17','0.1.0-r18'),
 ("r/'k275-main-candidates'","r/'k277-package-candidates'"),('original_signed_r22_r17_packages','original_signed_r23_r18_packages')]:s=s.replace(a,b)
a="assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'";assert s.count(a)==1;s=s.replace(a,a+"\nassert not Path('/usr/share/libcamera/ipa/simple/s5kgw1.yaml').exists(),'Existing module profile requires inspection before replacement'")
compile(s,'stage-r24.py','exec');(R/'stage-r24.py').write_text(s)
s=(R.parent/'kernel277/install-r23-worker.py').read_text()
for a,b in [('k277-package','k278-package'),('k277-services','k278-services'),('stage=277','stage=278'),('r23','r24'),('r22','r23'),('0.1.0-r18','0.1.0-r19'),('0.1.0-r17','0.1.0-r18'),
 ('physical_focus_metadata_validation_pending=True','physical_autofocus_validation_pending=True')]:s=s.replace(a,b)
compile(s,'install-r24-worker.py','exec');(R/'install-r24-worker.py').write_text(s)
s=(R.parent/'kernel277/install-r23.py').read_text().replace('install-r23-worker.py','install-r24-worker.py').replace('k277-package','k278-package')
compile(s,'install-r24.py','exec');(R/'install-r24.py').write_text(s)
print('r24-r2 full-feature QA and signed package-only transaction prepared')
