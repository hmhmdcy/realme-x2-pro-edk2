"""Prepare signed seven-package deployment with the existing r13 rollback."""
from pathlib import Path
import ast,hashlib,json,re,shutil,subprocess,tarfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239');ROOT=R.parents[1]
assert json.loads((R/'r15-startup-analysis.json').read_text())['r15_initial_snapshot_verified']
for kind in ['raw','rgb']:assert json.loads((R/f'front-{kind}-validation.json').read_text())['passed']
complete=P/'camera-forward-repo-r15';manifest=json.loads((complete/'package-manifest.json').read_text());selected={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
packages=[p for p in manifest['packages'] if p['name'] in selected];assert len(packages)==7
out=P/'camera-runtime-repo-r15';assert not out.exists();out.mkdir(mode=0o700);forward=out/'forward';forward.mkdir(mode=0o700)
for package in packages:shutil.copyfile(complete/package['file'],forward/package['file'])
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=P.parent/'kernel214/phone-trusted-public-keys';key=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
command=[str(apk),'--keys-dir',str(keys),'mkndx','--compression','deflate:9','--sign-key',str(key),'--pkgname-spec','${name}-${version}.apk','--description','Realme X2 Pro camera r15 runtime','--output',str(forward/'packages.adb'),*[str(p) for p in sorted(forward.glob('*.apk'))]]
result=subprocess.run(command,capture_output=True,timeout=60);(P/'runtime-index-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
result=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(forward/'packages.adb')],capture_output=True,timeout=20);(P/'runtime-index-verify-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
(out/'forward-manifest.json').write_text(json.dumps(dict(stage=239,packages=packages),indent=2)+'\n')
archive=P/'r15-seven-package-repo-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for p in sorted(out.rglob('*')):
  if p.is_file():tar.add(p,arcname=str(p.relative_to(out)),recursive=False)
(P/'seven-package-bundle-private.json').write_text(json.dumps(dict(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),indent=2)+'\n')
mapping={
 'k225-r13-package-candidates':'k239-r15-package-candidates','k225-r13-package-transaction':'k239-r15-package-transaction',
 'k225-baseline/boot-id-private.txt':'k236-runtime/boot-id-private.txt','k225-baseline/installed-before-private.txt':'k236-baseline/installed-before-private.txt',
 'k224-r11-package-candidates':'k225-r13-package-candidates','stage=225':'stage=239',
 '99990.7.2-r13':'99990.7.2-r15','99990.7.2-r11':'99990.7.2-r13','0.1.0-r8':'0.1.0-r10','0.1.0-r6':'0.1.0-r8',
 'all_current_camera_payloads_match_r11_rollback':'all_current_camera_payloads_match_r13_rollback','same_current219_boot':'same_current236_boot',
 'native_seven_package_r11_downgrade_simulation_passed':'native_seven_package_r13_downgrade_simulation_passed',
 'original_world_repositories_and_r11_payloads_retained':'original_world_repositories_and_r13_payloads_retained',
 'native signed seven-camera-package r8 upgrade':'native signed seven-camera-package r10 upgrade'}
pattern=re.compile('|'.join(re.escape(k) for k in sorted(mapping,key=len,reverse=True)))
for old,new in [('native-r13-preflight.py','native-r15-preflight.py'),('install-r13-packages.py','install-r15-packages.py')]:
 tree=ast.parse((R.parent/'kernel225'/old).read_text());node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets));code=pattern.sub(lambda m:mapping[m[0]],ast.literal_eval(node.value))
 ast.parse(code)
 header="from pathlib import Path\nimport json\nimport host\nR=Path(__file__).resolve().parent\n"
 if old.startswith('install'):header+="assert json.loads((R/'r15-native-preflight-validation.json').read_text())['native_phone_solver_passed']\n"
 validation='r15-native-preflight-validation.json' if old.startswith('native') else 'r15-package-install-validation.json'
 text=header+'code='+repr(code)+"\nresult=host.ssh('python3 -',input=code.encode(),timeout=110)\n(host.PRIVATE/"+repr(new+'-host-private.log')+").write_bytes(result.stdout+result.stderr)\nreport=json.loads(result.stdout)\n(R/"+repr(validation)+").write_text(json.dumps(report,indent=2)+'\\n')\nprint(json.dumps(report))\n"
 ast.parse(text);(R/new).write_text(text)
report=dict(stage=239,signed_seven_runtime_repository_prepared=True,full13_packages_retained=True,native_solver_and_actual_transaction_still_pending=True,r13_rollback_location_retained=True)
(R/'r15-install-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
