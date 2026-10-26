from pathlib import Path
import hashlib,json,shutil

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel225')
proof=json.loads((here.parent/'kernel224/lifecycle-probe-build-validation.json').read_text())
data=(private.parent/'kernel224/raw-lifecycle-probe').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['binary_sha256']
target=private/'raw-lifecycle-probe';assert not target.exists();target.write_bytes(data)
shutil.copyfile(here.parent/'kernel224/raw-lifecycle-probe.cpp',here/'raw-lifecycle-probe.cpp')
proof.update(stage=225,unchanged_stage224_binary_and_assertions=True)
(here/'lifecycle-probe-build-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
text=(here.parent/'kernel224/run-r11-lifecycle.py').read_text()
for a,b in [('r11-staging-validation.json','r13-staging-validation.json'),('new_r11_camera_libraries_loaded','new_r13_camera_libraries_loaded'),('k224-baseline','k225-baseline'),("'k224-capture-'","'k225-capture-'"),('stage=224','stage=225'),('samurai-camera224-r11','samurai-camera225-r13'),('samurai-camera224-probes','samurai-camera225-probes'),('lifecycle-r11-','lifecycle-r13-'),('99990.7.2-r11','99990.7.2-r13')]:text=text.replace(a,b)
compile(text,'run-r13-lifecycle.py','exec');(here/'run-r13-lifecycle.py').write_text(text)
print('Unchanged lifecycle binary and assertions prepared against R13 candidate.')
