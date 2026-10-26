from pathlib import Path
import hashlib,json,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-solver-before');apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=private/'phone-trusted-public-keys'
assert json.loads((here/'forward-package-artifact-validation.json').read_text())['all_signatures_verified_with_current_phone_trust']
repo=private/'camera-forward-repo';repositories=private/'solver-forward-repositories-private.list';repositories.write_text('ndx file://'+str(repo/'packages.adb')+'\n')
before=(root/'lib/apk/db/installed').read_bytes();world=(root/'etc/apk/world').read_bytes()
command=[str(apk),'--root',str(root),'--arch','aarch64','--no-network','--keys-dir',str(keys),'--repositories-file',str(repositories),'add','--simulate','samurai-camera-stack=0.1.0-r0']
p=subprocess.run(command,capture_output=True,text=True,timeout=60);(private/'solver-forward-dry-run-private.log').write_text(p.stdout+p.stderr)
assert before==(root/'lib/apk/db/installed').read_bytes() and world==(root/'etc/apk/world').read_bytes()
constraints=[line for line in world.decode().splitlines() if line.split('=')[0].split('@')[0] in ['libcamera','libcamera-ipa','libcamera-tools']]
report=dict(stage=214,solver_exit=p.returncode,actual940_package_database_used=True,package_database_and_world_unchanged=True,no_real_transaction_sent=True,current_camera_world_constraints=constraints,output=p.stdout+p.stderr)
(private/'solver-forward-result-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
