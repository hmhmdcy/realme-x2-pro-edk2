from pathlib import Path
import hashlib, json, subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel112/stock-hardware-reference')
repo = Path('/home/cy122/x2pro-linux/refs/realme-x2pro-androidr-project-k112')
metadata = json.loads((out / 'sources.json').read_text())
for name, digest in metadata['hashes'].items():
    assert hashlib.sha256((out / Path(name).name).read_bytes()).hexdigest() == digest
driver = (out / 'sensors_ssc.c').read_bytes()
assert driver == subprocess.check_output(['git','show','HEAD:drivers/sensors/sensors_ssc.c'], cwd=repo)
metadata['hashes']['drivers/sensors/sensors_ssc.c'] = hashlib.sha256(driver).hexdigest()
for name in ['OplusKernelEnvConfig.mk', 'oplus_native_features.mk']:
    data = subprocess.check_output(['git','show','HEAD:' + name], cwd=repo)
    (out / name).write_bytes(data)
    metadata['hashes'][name] = hashlib.sha256(data).hexdigest()
assert 'OPLUS_BUG_STABILITY' in (out / 'oplus_native_features.mk').read_text()
(out / 'sources.json').write_text(json.dumps(metadata, indent=2)+'\n')
print('Official board/SSC/feature sources verified; AP supply sequence identified, physical sensor function still untested')
