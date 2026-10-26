from pathlib import Path
import subprocess,os,json,hashlib,urllib.request
work=Path('/home/cy122/x2pro-linux/schema-k194');assert not work.exists();work.mkdir(mode=0o700)
out=Path('/mnt/e/edk2-samurai-out/kernel194');env=dict(os.environ,PIP_CONFIG_FILE='/dev/null',PIP_DISABLE_PIP_VERSION_CHECK='1')
with urllib.request.urlopen('https://pypi.org/pypi/dtschema/2026.9/json',timeout=25) as response:metadata=json.load(response)
assert metadata['info']['version']=='2026.9';(out/'dtschema-metadata-private.json').write_text(json.dumps(metadata,indent=2))
subprocess.run(['python3','-m','venv','--system-site-packages',str(work/'venv')],check=True,capture_output=True)
with (out/'schema-runtime-install-private.log').open('xb') as log:subprocess.run([str(work/'venv/bin/python'),'-m','pip','install','--index-url','https://pypi.org/simple','dtschema==2026.9'],stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=180)
actual=subprocess.check_output([str(work/'venv/bin/python'),'-c','import dtschema,libfdt;print(dtschema.__version__)'],text=True).strip();assert actual=='2026.9'
print(json.dumps(dict(stage=194,isolated_schema_runtime=True,version=actual,system_packages_unchanged=True)))
