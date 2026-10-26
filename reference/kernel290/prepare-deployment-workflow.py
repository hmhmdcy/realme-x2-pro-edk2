"""Adapt the verified complete-kernel workflow to an independent kernel290 release."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel288'
def write(name,text):
 p=ROOT/name;assert not p.exists();compile(text,name,'exec') if p.suffix=='.py' else None;p.write_text(text)

s=(OLD/'audit-preserved-sources.py').read_text().replace('stage=288','stage=290');write('audit-preserved-sources.py',s)
s=(OLD/'package-boot-candidate.py').read_text()
for a,b in [('/mnt/e/edk2-samurai-out/kernel288','/mnt/e/edk2-samurai-out/kernel290'),('input-initramfs288','input-initramfs290'),
 ('modules-pix288-private.tar.gz','modules-k290-private.tar.gz'),("kernel183/logdump-k183-offline-stream.img","kernel288/logdump-pix288-candidate-private.img"),
 ('e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358','8ec8b1e4d28ed76906ac9c9d31d8d791cab9d190c28d7f27224f8fb47e4aa56c'),
 ('logdump-pix288-candidate-private.img','logdump-k290-candidate-private.img'),('Image-pix288-private','Image-k290-private'),('stage=288','stage=290'),('kernel_build=288','kernel_build=290')]:s=s.replace(a,b)
# The template/rollback path was renamed by the broad output filename substitution.
s=s.replace("kernel288/logdump-k290-candidate-private.img","kernel288/logdump-pix288-candidate-private.img")
write('package-boot-candidate.py',s)

s=(OLD/'stage-device-modules.py').read_text().replace('k288','k290').replace('stage=288','stage=290')
s=s.replace('modules-pix288-private.tar.gz','modules-k290-private.tar.gz')
s=s.replace("assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k132+'","assert os.uname().version.startswith('#288 ') and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k279candidate+'")
s=s.replace("Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k279candidate+')","Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k290+')")
s=s.replace('len(before)==776','len(before)==778').replace('all776_running_release_modules_preserved','all778_running_release_modules_preserved')
write('stage-device-modules.py',s)

for name in ['native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py']:
 s=(OLD/name).read_text().replace('k288','k290').replace('stage=288','stage=290').replace('k276-work','k288-work').replace("'#183 '","'#288 '")
 write(name,s)
s=(OLD/'flash-logdump.py').read_text().replace('stage=288','stage=290').replace("package['kernel_build']==288","package['kernel_build']==290")
write('flash-logdump.py',s)
s=(OLD/'refresh-usb-endpoint.ps1').read_text().replace('kernel288','kernel290').replace('K288','K290');write('refresh-usb-endpoint.ps1',s)
s=(OLD/'bootstrap-postboot.py').read_text().replace('k288','k290').replace('stage=288','stage=290').replace('kernel_build=288','kernel_build=290').replace('k276-work','k288-work').replace("'#288 '","'#290 '")
write('bootstrap-postboot.py',s)
print('Prepared independent-release deployment scripts; no device mutation or transition submitted.')
