from pathlib import Path
import runpy,subprocess,urllib.request,json,os
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118/camera120');venv=root/'schema-venv'
out=Path('/mnt/e/edk2-samurai-out/kernel120')
with urllib.request.urlopen('https://pypi.org/pypi/dtschema/json',timeout=20) as r:metadata=json.load(r)
version=metadata['info']['version']
assert all(c in '0123456789.' for c in version)
subprocess.run(['python3','-m','venv','--system-site-packages',str(venv)],check=True,timeout=30)
env=dict(os.environ,TMPDIR=str(root),PIP_CACHE_DIR=str(root/'pip-cache'),PIP_CONFIG_FILE='/dev/null')
with (out/'schema-tools-install-private.txt').open('w') as log:
    subprocess.run([str(venv/'bin/python'),'-m','pip','install','--index-url','https://pypi.org/simple',f'dtschema=={version}'],stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=180)
actual=subprocess.check_output([str(venv/'bin/python'),'-c','import dtschema;print(dtschema.__version__)'],text=True).strip();assert actual==version
report=dict(dtschema_version=version,pypi_metadata_url='https://pypi.org/pypi/dtschema/json',installed_on_e_volume=True,phone_unchanged=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120/schema-tools-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
