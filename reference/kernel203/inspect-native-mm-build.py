from pathlib import Path
import hashlib,json,os,subprocess

root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k203-baseline/boot-id-private.txt').read_bytes()
out=root/'k203-mm-inspection';assert not out.exists();out.mkdir(mode=0o700)
base=root/'k190-mm-build';sdk=root/'k190-mm-sdk';source=next((base/'source').iterdir());env=json.loads((base/'build-environment-private.json').read_text())
assert hashlib.sha256((source/'src/mm-shared-qmi.c').read_bytes()).hexdigest()=='949132f3203b78300224a1fb958cbd1fa44202661f35f64dbed4f84f3ff5ed24'
for name,args in [('ninja-dry-run',[str(sdk/'usr/bin/ninja'),'-C',str(base/'build'),'-n']),('package-files',['apk','info','-L','modemmanager']),('package-version',['apk','list','--installed','modemmanager']),('library-version',['apk','list','--installed','libmm-glib']),('libmm-package-files',['apk','info','-L','libmm-glib'])]:
 p=subprocess.run(args,capture_output=True,text=True,timeout=30,env=env if name=='ninja-dry-run' else None);(out/(name+'-private.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,name
ownership={}
for path in ['/usr/lib/girepository-1.0/Qmi-1.0.typelib','/usr/lib/girepository-1.0/Qrtr-1.0.typelib','/etc/init.d/chronyd','/etc/init.d/dbus']:
 p=subprocess.run(['apk','info','-W',path],capture_output=True,text=True,timeout=10);assert p.returncode==0;ownership[Path(path).name]=p.stdout.strip().split(' owned by ',1)[-1]
r=dict(stage=203,same_current_boot=True,mm191_source_exact=True,modemmanager_installed_version=(out/'package-version-private.txt').read_text().strip(),libmm_installed_version=(out/'library-version-private.txt').read_text().strip(),dry_run_lines=len((out/'ninja-dry-run-private.txt').read_text().splitlines()),runtime_dependency_owners=ownership,source_directory=source.name,build_targets_not_executed=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
