"""Remove obsolete camera OF bring-up helpers in a separate maintenance candidate."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269');P.mkdir(mode=0o700)
U=Path('/home/cy122/x2pro-linux/upstream');G=['git','-c','safe.directory='+str(U),'-C',str(U)]
def git(*args):return subprocess.check_output(G+list(args),text=True).rstrip()
parent='db301b64c0c591f63423d278643d452294654324';assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
assert not git('branch','--list','samurai-camera-common')
subprocess.run(G+['switch','-c','samurai-camera-common'],check=True)
sources=['samurai-cci-bringup.c','samurai-front-identify.c','samurai-pmic-fixture.c','samurai-vio-phandle.c','samurai-front-overlay.c']
configs=['OF_SAMURAI_CCI_BRINGUP','OF_SAMURAI_FRONT_IDENTIFY','OF_SAMURAI_PMIC_FIXTURE','OF_SAMURAI_VIO_PHANDLE','OF_SAMURAI_FRONT_OVERLAY']
config=Path('/home/cy122/x2pro-linux/camera268-maintained-build-r2/.config').read_text()
assert all('# CONFIG_'+name+' is not set' in config for name in configs)
for n,digest in json.loads((R.parent/'kernel268/maintained-source-validation.json').read_text())['source_files_sha256'].items():
 assert hashlib.sha256((U/n).read_bytes()).hexdigest()==digest
deleted={n:hashlib.sha256((U/'drivers/of'/n).read_bytes()).hexdigest() for n in sources}
k=U/'drivers/of/Kconfig';s=k.read_text();marker='\nconfig OF_SAMURAI_CCI_BRINGUP\n';assert s.count(marker)==1
assert all('config '+n+'\n' in s[s.index(marker):] for n in configs)
k.write_text(s[:s.index(marker)].rstrip()+'\n')
m=U/'drivers/of/Makefile';lines=m.read_text().splitlines()
lines=[l for l in lines if not any('CONFIG_'+n+')' in l for n in configs)];m.write_text('\n'.join(lines).rstrip()+'\n')
subprocess.run(G+['rm','--',*['drivers/of/'+n for n in sources]],check=True)
subprocess.run(G+['add','--','drivers/of/Kconfig','drivers/of/Makefile'],check=True)
subprocess.run(G+['diff','--cached','--check'],check=True)
body=P/'cleanup-commit-message.txt';body.write_text('of: remove obsolete RMX1931 camera bring-up helpers\n\nThe static board tree now describes the CCI buses, both PM8008 devices, sensor supply phandles and camera endpoints. Common MFD/regulator and sensor drivers have passed native cam and unchanged Snapshot front/rear capture on the phone.\n\nRemove the unused dynamic node fixtures, identification helper, overlay loader and their Kconfig/Makefile entries from this separate maintenance candidate. All five options were disabled in the deployed configuration. Keep their historical implementations in the original bring-up branch and Git history.\n')
subprocess.run(G+['commit','--file',str(body)],check=True)
assert not git('status','--porcelain')
report=dict(stage=269,branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),parent=parent,
 removed_unused_sources_sha256=deleted,removed_configs=configs,all_five_disabled_in_previous_build=True,
 deployed_camera_inputs_preserved=True,original_bringup_branch_preserved=git('rev-parse','samurai-bringup')==parent,
 phone_not_modified=True)
(R/'cleanup-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
