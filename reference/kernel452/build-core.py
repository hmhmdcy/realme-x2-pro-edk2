from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
sys.dont_write_bytecode=True
import storage

HERE=Path(__file__).resolve().parent
PRIVATE=Path("/mnt/e/edk2-samurai-out/kernel452")
PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
volume=storage.mount.mounted_build().parent
tree=storage.candidate()/"src/libcamera-v0.7.2"
state=json.loads((HERE/"source-state.json").read_text())
base=json.loads((HERE.parent/"kernel450/build-validation.json").read_text())
assert state["diagnostic_only"] and state["full_ownership_trace_default_disabled"] and base["passed"]
paths={
    "libcamera.so.0.7.2":"output/src/libcamera/libcamera.so.0.7.2",
    "ipa_camss_vfe.so":"output/src/ipa/camss-vfe/ipa_camss_vfe.so",
    "ipa_camss_vfe.so.sign":"output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign",
    "camss_ipa_proxy":"output/src/libcamera/proxy/worker/camss_ipa_proxy",
}
expected={row["name"]:row["sha256"] for row in base["runtime_files"]}
def unchanged():
    for row in state["source_hashes"]:
        assert hashlib.sha256((tree/row["path"]).read_bytes()).hexdigest()==row["sha256"],row["path"]
def baseline_unchanged():
    original=volume/"libcamera450-stats-retirement/src/libcamera-v0.7.2"
    old=json.loads((HERE.parent/"kernel450/source-state.json").read_text())
    for row in old["source_hashes"]:
        assert hashlib.sha256((original/row["path"]).read_bytes()).hexdigest()==row["sha256"]
    for name,relative in paths.items():
        assert hashlib.sha256((original/relative).read_bytes()).hexdigest()==expected[name]
unchanged();baseline_unchanged()
attempt=1
while (PRIVATE/f"core-build-r{attempt}.log").exists() or (PRIVATE/f"core-plan-r{attempt}.log").exists():
    attempt+=1
for name,relative in paths.items():
    if name!="libcamera.so.0.7.2" or attempt==1:
        assert hashlib.sha256((tree/relative).read_bytes()).hexdigest()==expected[name]
target=["ninja","-C","/work/libcamera/src/libcamera-v0.7.2/output","-j4","src/libcamera/libcamera.so.0.7.2"]
start=time.monotonic()
version=tree/"output/src/libcamera/version.cpp"
version_before=hashlib.sha256(version.read_bytes()).hexdigest()
with storage.sdk_candidate():
    plan=subprocess.run(["chroot",str(storage.SDK),*target[:3],"-n",*target[3:]],capture_output=True)
    planlog=plan.stdout+plan.stderr
    (PRIVATE/f"core-plan-r{attempt}.log").write_bytes(planlog)
    steps=[line for line in planlog.decode().splitlines() if re.match(r"^\[\d+/\d+\]",line)]
    allowed=[
        "Compiling C++ object src/libcamera/libcamera.so.0.7.2.p/pipeline_camss-vfe_camss_vfe.cpp.o",
        "Generating src/libcamera/version.cpp with a custom command",
        "Compiling C++ object src/libcamera/libcamera.so.0.7.2.p/meson-generated_.._version.cpp.o",
        "Linking target src/libcamera/libcamera.so.0.7.2",
    ]
    assert not plan.returncode and len(steps) in (2,4),planlog.decode()
    assert all(any(label in step for label in allowed) for step in steps),steps
    assert any(allowed[0] in step for step in steps) and any(allowed[-1] in step for step in steps),steps
    print(json.dumps({"stage":452,"attempt":attempt,"build_started":True,"planned_steps":steps}),flush=True)
    run=subprocess.run(["chroot",str(storage.SDK),*target],capture_output=True)
    (PRIVATE/f"core-build-r{attempt}.log").write_bytes(run.stdout+run.stderr)
executed=[line for line in (run.stdout+run.stderr).decode().splitlines()
          if re.match(r"^\[\d+/\d+\]",line)]
unmounted=subprocess.run(["mountpoint","-q",str(storage.SDK/"work/libcamera")],capture_output=True).returncode!=0
report={
    "stage":452,"attempt":attempt,"exit_code":run.returncode,
    "seconds":round(time.monotonic()-start,2),"sdk_bind_unmounted":unmounted,
    "requested_only_core_target":True,"planned_steps":steps,"executed_steps":executed,
    "diagnostic_only":True,
    "default_disabled":True,"phone_accessed":False,"installed":False,
    "private_ipa_version":6,"passed":False,
}
(HERE/f"build-r{attempt}-validation.json").write_text(json.dumps(report,indent=2)+"\n")
print((run.stdout+run.stderr).decode()[-5000:],flush=True)
assert not run.returncode and unmounted
unchanged();baseline_unchanged()
assert hashlib.sha256(version.read_bytes()).hexdigest()==version_before,"Generated version content changed"
files=[]
for name,relative in paths.items():
    path=tree/relative
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if name=="libcamera.so.0.7.2":
        assert digest!=expected[name]
        shutil.copyfile(path,PRIVATE/name)
    else:
        assert digest==expected[name],name+" changed unexpectedly"
    files.append({"name":name,"bytes":path.stat().st_size,"sha256":digest})
report.update(runtime_files=files,source_inputs_unchanged_during_build=True,
              baseline450_preserved=True,ipa_proxy_signature_preserved=True,
              generated_version_content_unchanged=True,passed=True)
(HERE/"build-validation.json").write_text(json.dumps(report,indent=2)+"\n")
(HERE/f"build-r{attempt}-validation.json").write_text(json.dumps(report,indent=2)+"\n")
state["build_pending"]=False
state["successful_build"]=attempt
(HERE/"source-state.json").write_text(json.dumps(state,indent=2)+"\n")
print(json.dumps(report,indent=2),flush=True)
