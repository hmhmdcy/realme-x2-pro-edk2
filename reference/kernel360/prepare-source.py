"""Merge preserved Gamma and factory AE candidates over their common baseline."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;new=storage.candidate();common=new.parent/'libcamera342-r27-built/src/libcamera-v0.7.2'
exposure=new.parent/'libcamera359-exposure-built';gamma=new.parent/'libcamera349-gamma-built/src/libcamera-v0.7.2'
assert not new.exists()
for name in ['AGENTS.md','src/AGENTS.md','src/ipa/AGENTS.md','src/ipa/camss-vfe/AGENTS.md','src/ipa/libipa/AGENTS.md','include/AGENTS.md']:
    assert not (exposure/'src/libcamera-v0.7.2'/name).exists(),'Read '+name
shutil.copytree(exposure,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';state=json.loads((HERE.parent/'kernel349/source-state.json').read_text());rows=[]
for name in state['changed_sources']:
    ours=tree/name;base=common/name;theirs=gamma/name
    assert hashlib.sha256(theirs.read_bytes()).hexdigest()==state['source_sha256'][name]
    if not base.exists() or ours.read_bytes()==base.read_bytes():
        assert not ours.exists() or base.exists();ours.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(theirs,ours);method='unmodified-base'
    else:
        q=subprocess.run(['git','merge-file','-p',str(ours),str(base),str(theirs)],capture_output=True)
        (host.PRIVATE/(ours.name+'-merge-output-private.txt')).write_bytes(q.stdout+q.stderr)
        assert q.returncode in [0,1],(name,q.stderr.decode())
        if q.returncode:
            # Both branches extend the same one-line source array.
            assert name=='src/ipa/camss-vfe/meson.build',(name,'inspect preserved conflict')
            text=ours.read_text();needle="'dynamic_lens_shading.cpp', 'exposure_program.cpp']"
            assert text.count(needle)==1
            ours.write_text(text.replace(needle,"'dynamic_lens_shading.cpp', 'exposure_program.cpp', 'gamma_profile.cpp']"));method='merged-source-array'
        else:ours.write_bytes(q.stdout);method='three-way'
    rows.append(dict(path=name,merge=method,sha256=hashlib.sha256(ours.read_bytes()).hexdigest()))
assert 'IPA_MODULE_API_VERSION, 1, "camss-vfe"' in (tree/'src/ipa/camss-vfe/camss.cpp').read_text()
assert (tree/'include/libcamera/ipa/camss.mojom').read_bytes()==(exposure/'src/libcamera-v0.7.2/include/libcamera/ipa/camss.mojom').read_bytes()
(HERE/'merge-validation.json').write_text(json.dumps(dict(stage=360,source=str(tree),base_stage=342,exposure_stage=359,gamma_stage=349,files=rows,
    camss_pipeline_version=1,private_factory_tuning_not_in_source=True,installed=False,passed=True),indent=2)+'\n')
print(json.dumps(dict(stage=360,source=str(tree),merged_gamma_files=len(rows),passed=True)))
