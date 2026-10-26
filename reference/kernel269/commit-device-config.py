"""Verify and commit only the two reviewed board configuration changes."""
from pathlib import Path
import hashlib,json,re,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269');U=Path('/home/cy122/x2pro-linux/pmaports-camera-common269')
G=['git','-c','safe.directory='+str(U),'-C',str(U)];counts={}
for name in ['samurai-platform','samurai-desktop']:
 pkg=U/'device/testing'/name;text=(pkg/'APKBUILD').read_text();subprocess.run(['sh','-n',str(pkg/'APKBUILD')],check=True)
 sums=re.search(r'sha512sums="\n(.*?)\n"',text,re.S).group(1).splitlines()
 for line in sums:
  digest,file=line.split();assert '/' not in file and hashlib.sha512((pkg/file).read_bytes()).hexdigest()==digest
 counts[name]=len(sums)
paths=['device/testing/samurai-platform/APKBUILD','device/testing/samurai-platform/etc_modprobe.d_samurai-pmic-bringup.conf',
 'device/testing/samurai-platform/99-realme-rmx1931-sensors.rules','device/testing/samurai-desktop/APKBUILD','device/testing/samurai-desktop/greetd.confd']
subprocess.run(G+['add','--',*paths],check=True);subprocess.run(G+['diff','--cached','--check'],check=True)
assert set(subprocess.check_output(G+['diff','--cached','--name-only'],text=True).splitlines())==set(paths)
body=P/'device-config-commit-message.txt';body.write_text('device/realme-samurai: describe sensor alignment and service ordering\n\nSupply the standard SensorProxy SSC accelerometer mount matrix in the device platform package. Both portrait and left-up were inverted before correction; the phone user confirmed automatic rotation after applying the matrix and reconnecting the ready desktop session. Keep all direction policy out of Phosh and camera applications.\n\nOrder greetd after its standard SensorProxy dependency, removing the opposing before-radio edge. The existing SSC service owns radio and firmware readiness. The dependency cache update succeeds; a fresh-boot check remains pending.\n\nRemove the obsolete experimental PM8008 power option and board reset softdep from the candidate device recipe now that common MFD/regulator drivers and DT wiring provide camera supplies. Preserve all unrelated device configuration and the existing Cairo Snapshot fallback.\n')
subprocess.run(G+['commit','--file',str(body)],check=True)
assert not subprocess.check_output(G+['status','--porcelain']).strip()
report=dict(stage=269,commit=subprocess.check_output(G+['rev-parse','HEAD'],text=True).strip(),branch='samurai-camera-common',
 source_checksum_counts=counts,source_clean=True,apk_build_and_install_pending=True,publication_pending=True,
 desktop_and_camera_application_sources_unchanged=True)
(R/'device-config-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
