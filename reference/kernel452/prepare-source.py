from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
sys.dont_write_bytecode=True
import storage

HERE=Path(__file__).resolve().parent
PRIVATE=Path("/mnt/e/edk2-samurai-out/kernel452")
PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
volume=storage.mount.mounted_build().parent
baseline=volume/"libcamera450-stats-retirement"
new=storage.candidate()
assert not new.exists(),"Never overwrite a candidate"
state=json.loads((HERE.parent/"kernel450/source-state.json").read_text())
proof=json.loads((HERE/"source-draft-validation.json").read_text())
ring=json.loads((HERE/"ring-validation.json").read_text())
assert proof["passed"] and ring["passed"]
patch=HERE/"0063-camss-bounded-full-ownership-trace.patch"
assert hashlib.sha256(patch.read_bytes()).hexdigest()==proof["patch_sha256"]
for row in state["source_hashes"]:
    assert hashlib.sha256((baseline/"src/libcamera-v0.7.2"/row["path"]).read_bytes()).hexdigest()==row["sha256"]
usage=sum(path.stat().st_size for path in baseline.rglob("*") if path.is_file() and not path.is_symlink())
free=os.statvfs(volume).f_bavail*os.statvfs(volume).f_frsize
assert free > usage+1024**3,(free,usage)
shutil.copytree(baseline,new,symlinks=True,
                ignore=lambda folder,names:[name for name in names if name=="pkg" or name.startswith("pkg-before") or name=="__pycache__"])
tree=new/"src/libcamera-v0.7.2"
arguments=["patch","-p1","--batch","--fuzz=0","-i",str(patch)]
for kind,extra in [("dry-run",["--dry-run"]),("apply",[])]:
    run=subprocess.run(arguments+extra,cwd=tree,capture_output=True)
    log=run.stdout+run.stderr
    (PRIVATE/("patch-"+kind+".log")).write_bytes(log)
    assert run.returncode==0 and b"offset" not in log.lower() and b"fuzz" not in log.lower(),log.decode()
pipeline="src/libcamera/pipeline/camss-vfe/camss_vfe.cpp"
header="src/libcamera/pipeline/camss-vfe/full_ownership_trace.h"
assert hashlib.sha256((tree/pipeline).read_bytes()).hexdigest()==proof["draft_pipeline_sha256"]
assert hashlib.sha256((tree/header).read_bytes()).hexdigest()==ring["header_sha256"]
for row in state["source_hashes"]:
    digest=hashlib.sha256((tree/row["path"]).read_bytes()).hexdigest()
    if row["path"]!=pipeline:
        assert digest==row["sha256"]
    row["sha256"]=digest
state["source_hashes"].append({"path":header,"sha256":ring["header_sha256"]})
state.update(stage=452,source=str(tree),baseline_stage=450,source_baseline_stage=450,
             changed_this_stage=[pipeline,header],diagnostic_only=True,build_pending=True,
             full_ownership_trace_default_disabled=True)
(HERE/"source-state.json").write_text(json.dumps(state,indent=2)+"\n")
result={
    "stage":452,"free_before_copy_bytes":free,"baseline_tree_bytes":usage,
    "patch_sha256":proof["patch_sha256"],"patch_zero_fuzz_and_offset":True,
    "source":str(tree),"changed_this_stage":[pipeline,header],
    "ipa_protocol_af_tuning_preserved":True,"baseline450_preserved":True,
    "phone_accessed":False,"passed":True,
}
(HERE/"source-validation.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2),flush=True)
