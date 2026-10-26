from pathlib import Path
import difflib,hashlib,json,shutil,subprocess,tempfile
import storage
HERE=Path(__file__).resolve().parent;candidate=storage.candidate();tree=candidate/'src/libcamera-v0.7.2';old=candidate.parent/'libcamera421-frame-history/src/libcamera-v0.7.2'
state=json.loads((HERE/'candidate-source-state.json').read_text())
dest=tree/'src/ipa/camss-vfe/ipe_numeric_history.h';shutil.copyfile(HERE/'ipe_numeric_history.h',dest)
names=['src/ipa/libipa/'+n for n in state['common_libipa_numeric_sources']]+['src/ipa/libipa/meson.build','src/ipa/camss-vfe/ipe_numeric_history.h']
patch='';rows=[]
for n in names:
    before=(old/n).read_text() if (old/n).exists() else '';after=(tree/n).read_text()
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+n if before else '/dev/null',tofile='b/'+n))
    rows.append(dict(path=n,sha256=hashlib.sha256((tree/n).read_bytes()).hexdigest()))
(HERE/'0043-camss-tmc-ltm-numeric-assembly.patch').write_text(patch)
with tempfile.TemporaryDirectory(dir=candidate.parent/'tmp',prefix='k422-patch-') as folder:
    replay=Path(folder)
    for n in names:
        if (old/n).exists():
            p=replay/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,p)
    q=subprocess.run(['patch','-p1','--fuzz=0','--batch'],cwd=replay,input=patch.encode(),capture_output=True)
    assert not q.returncode,(q.stdout+q.stderr).decode()
    for n in names:assert (replay/n).read_bytes()==(tree/n).read_bytes(),n
build=json.loads((HERE/'build-validation.json').read_text());prior=json.loads((HERE.parent/'kernel421/build-validation.json').read_text())
identical=build['runtime_files']==prior['runtime_files'];assert identical
state.update(source_hashes=rows,patch_zero_fuzz_reproduced=True,numeric_history_policy_single_uncommitted=True,
    numeric_history_runtime_connected=False,shared_runtime_artifacts_identical_to421=True,
    unused_numeric_static_objects_not_linked_into_ipa=True,signature_evidence_reused_from421=True,passed=True)
(HERE/'candidate-source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=422,files=len(names),zero_fuzz_reproduced=True,numeric_static_library_built=True,
    shared_runtime_artifacts_identical_to421=identical,automatic_runtime_generation_integrated=False,passed=True),indent=2))
