from pathlib import Path
import hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2'
state=json.loads((HERE.parent/'kernel437/source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((T/row['path']).read_bytes()).hexdigest()==row['sha256']
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
build=json.loads((HERE.parent/'kernel437/build-validation.json').read_text());assert build['passed']
for row in build['runtime_files']:
 path=P.parent/'kernel437'/row['name'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'];shutil.copyfile(path,P/row['name'])
build.update(stage=438,reused_userspace_stage437=True,source_and_binary_unchanged=True)
(HERE/'build-validation.json').write_text(json.dumps(build,indent=2)+'\n')
for name in ['capture','factory-s5kgw1-private.yaml']:shutil.copyfile(P.parent/'kernel437'/name,P/name)
for name in ['capture-validation.json','ipa-validation.json']:shutil.copyfile(HERE.parent/'kernel437'/name,HERE/name)
print('Matched437 library/IPA/signature/proxy and bounded capture reused for438 profiles')
