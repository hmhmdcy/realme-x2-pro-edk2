from pathlib import Path
import os,shutil,json,hashlib,subprocess
base=Path('/var/lib/samurai/k148-mesa');r=json.loads((base/'candidate-preparation.json').read_text())
assert hashlib.sha256((base/'mesa-26.2.4'/r['modified_file']).read_bytes()).hexdigest()==r['candidate_sha256']
assert hashlib.sha256((base/'baseline-build/libvulkan_freedreno.so').read_bytes()).hexdigest()==r['same_build_baseline_library_sha256']
candidate=base/'candidate-build/libvulkan_freedreno.so';shutil.copy2(base/'build/src/freedreno/vulkan/libvulkan_freedreno.so',candidate);os.chmod(candidate,0o755)
r.update(candidate_library_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
    installed_library_sha256=hashlib.sha256(Path('/usr/lib/libvulkan_freedreno.so').read_bytes()).hexdigest(),
    candidate_built=True,installed_library_changed=False)
with (base/'candidate-elf-private.log').open('wb') as f:
    subprocess.run(['/tmp/k148-sdk/usr/bin/readelf','-h','-d',str(candidate)],env=json.loads((base/'build-env-private.json').read_text()),stdout=f,stderr=subprocess.STDOUT,check=True)
(base/'candidate-preparation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
