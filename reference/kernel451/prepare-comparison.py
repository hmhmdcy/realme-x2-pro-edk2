"""Offline-only comparison preparation. This script has no remote operations."""
from pathlib import Path
import argparse
import ast
import hashlib
import io
import json
import shutil
import struct
import tarfile
import sys
sys.dont_write_bytecode=True

HERE=Path(__file__).resolve().parent
import storage
storage.mount.mounted_build()
PRIVATE=Path("/mnt/e/edk2-samurai-out/kernel451")
PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
parser=argparse.ArgumentParser()
parser.add_argument("--attempt",default="r1")
parser.add_argument("--handoff",type=Path)
parser.add_argument("--baseline",type=Path)
args=parser.parse_args()
assert args.attempt.startswith("r") and args.attempt[1:].isdigit() and 1<=int(args.attempt[1:])<=20
assert bool(args.handoff)==bool(args.baseline),"Supply both fresh handoff and baseline, or neither"
window="k451-proxy-comparison-"+args.attempt
work=PRIVATE/("comparison-prepared-"+args.attempt)
work.mkdir(mode=0o700,exist_ok=True)
assert not (work/"comparison-payload.tar.gz").exists(),"Inspect the existing ready bundle; never overwrite or reuse it blindly"
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

old=json.loads((HERE.parent/"kernel450/build-validation.json").read_text())
new=json.loads((HERE/"build-validation.json").read_text())
assert old["passed"] and new["passed"] and new["core450_ipa_signature_unchanged"]
old_hash={row["name"]:row["sha256"] for row in old["runtime_files"]}
new_hash={row["name"]:row["sha256"] for row in new["runtime_files"]}
assert all(old_hash[name]==new_hash[name] for name in old_hash if name!="camss_ipa_proxy")
assert old_hash["camss_ipa_proxy"]!=new_hash["camss_ipa_proxy"]
inputs=json.loads((PRIVATE.parent/"kernel450/runtime-input-files-private.json").read_text())
files={}
common={}
for name,row in inputs.items():
    path=Path(row["path"]);assert sha(path)==row["sha256"]
    if name=="proxy/camss_ipa_proxy":
        assert row["sha256"]==old_hash["camss_ipa_proxy"]
        files["proxy-old/camss_ipa_proxy"]=path
    else:
        files[name]=path;common[name]=row["sha256"]
assert common["lib/libcamera.so.0.7.2"]==old_hash["libcamera.so.0.7.2"]
assert common["ipa/ipa_camss_vfe.so"]==old_hash["ipa_camss_vfe.so"]
assert common["ipa/ipa_camss_vfe.so.sign"]==old_hash["ipa_camss_vfe.so.sign"]
files["proxy-new/camss_ipa_proxy"]=PRIVATE/"camss_ipa_proxy"
assert sha(files["proxy-new/camss_ipa_proxy"])==new_hash["camss_ipa_proxy"]
files["factory-s5kgw1-private.yaml"]=PRIVATE.parent/"kernel443/factory-s5kgw1-private.yaml"
files["gst-sustained"]=PRIVATE.parent/"kernel449/gst-sustained"
files["pipeline-fixture"]=PRIVATE.parent/"kernel449/pipeline-fixture-long"
files["user-launcher.py"]=HERE.parent/"kernel450/user-launcher.py"
clients=json.loads((HERE.parent/"kernel449/long-client-build-validation.json").read_text())
assert clients["passed"]
for row in clients["clients"]:
    assert sha(files[row["name"]])==row["sha256"]
for name in ["factory-s5kgw1-private.yaml","gst-sustained"]:
    common[name]=sha(files[name])
modules=json.loads((HERE.parent/"kernel441/intree-build-validation.json").read_text())
assert modules["passed"] and not modules["diagnostics"]
module_proof={}
for row in modules["modules"]:
    if not row["runtime_candidate"]:
        continue
    path=Path(row["private_path"]);raw=path.read_bytes()
    assert sha(path)==row["sha256"]
    shoff=struct.unpack_from("<Q",raw,40)[0]
    stride,count,strings=struct.unpack_from("<HHH",raw,58)
    sections=[struct.unpack_from("<IIQQQQIIQQ",raw,shoff+i*stride) for i in range(count)]
    names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
    note=next(section for section in sections if names[section[0]:].split(bytes([0]))[0]==b".note.gnu.build-id")
    filename=row["name"]+".ko";files[filename]=path
    module_proof[row["name"].replace("-","_")]=dict(file=filename,sha256=row["sha256"],
        note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest())

handoff=None
if args.handoff:
    handoff=json.loads(args.handoff.read_text())
    assert handoff["schema"]=="samurai-camera-handoff-v1"
    assert handoff["window_id"]==window and handoff["window_owner"]=="camera"
    assert handoff["fresh_preflight_verified"] is True and handoff["issued_at_utc"]
    assert handoff["formal_baseline_sha256"]==sha(args.baseline)
    assert len(handoff["formal_library_sha256"])==64 and Path(handoff["boot_guard_path"]).is_absolute()
    assert set(handoff["charging"])=={
        "manifest_sha256","notes","limits","source_type","source_budget_ua",
        "native_udc_allowance_ua","gadget_maxpower_ma","service_enabled",
        "native_retained","control_enabled",
    }
    files["handoff-private.json"]=args.handoff
    files["baseline-private.json"]=args.baseline
proof=dict(modules=module_proof,boot_guard=handoff["boot_guard_path"] if handoff else "FRESH_HANDOFF_REQUIRED")
(work/"proof.json").write_text(json.dumps(proof,indent=2)+"\n")
files["proof.json"]=work/"proof.json"
plan=dict(
    stage=451,window_id=window,kernel_release=modules["modules"][0]["vermagic"].split()[0],
    common_payload=common,segments=[
        dict(name="A1",kind="old",proxy_payload="proxy-old/camss_ipa_proxy",proxy_sha256=old_hash["camss_ipa_proxy"]),
        dict(name="B",kind="new",proxy_payload="proxy-new/camss_ipa_proxy",proxy_sha256=new_hash["camss_ipa_proxy"]),
        dict(name="A2",kind="old",proxy_payload="proxy-old/camss_ipa_proxy",proxy_sha256=old_hash["camss_ipa_proxy"]),
    ],target_frames_per_segment=180,isolated=True,width=1920,height=1080,
    observer_used=False,fixture_timeout_seconds=25,user_path_identical_all_segments=True,
    steady_window_first_frame_at_least=60,witness_guard_frames=8,
    fresh_handoff_required=True,automatic_stage_or_launch=False,
)
(work/"comparison-plan-private.json").write_text(json.dumps(plan,indent=2)+"\n")
files["comparison-plan-private.json"]=work/"comparison-plan-private.json"
files["capture-body-comparison.py"]=HERE/"capture-body-comparison.py"
for name in ["capture-body-comparison.py","check-comparison.py","observe-comparison.py"]:
    if (HERE/name).exists():
        ast.parse((HERE/name).read_text(),filename=name)
prefix=(HERE.parent/"kernel342/native-install.py").read_text().split("def versions():",1)[0]
prefix=prefix.replace("'stage':342","'stage':451")+"\nimport runpy\n"
body=(HERE.parent/"kernel434/capture-worker-body.py").read_text()
a=body.index(" state['captures']={}");z=body.index("\nexcept BaseException:",a)
body=body[:a]+""" comparison['run_comparison'](root,state,save,status,idle,core)
 verified=True
"""+body[z:]
needle="try:\n assert Path('/proc/sys/kernel/random/boot_id')"
assert body.count(needle)==1
body=body.replace(needle,"""comparison=runpy.run_path(str(root/'capture-body-comparison.py'))
try:
 comparison['validate_handoff'](root,state)
 assert Path('/proc/sys/kernel/random/boot_id')""")
needle="  state['after_status']=status();state['after_core']=core();assert released(core())"
assert body.count(needle)==1
body=body.replace(needle,needle+"\n  state['comparison_final_checks']=comparison['finalize'](root,state)")
worker=prefix+body
ast.parse(worker,filename="comparison-worker.py")
(work/"worker.py").write_text(worker)
files["worker.py"]=work/"worker.py"
manifest={name:sha(path) for name,path in files.items()}
(work/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
files["manifest.json"]=work/"manifest.json"
(work/"payload-files-private.json").write_text(json.dumps({name:str(path) for name,path in files.items()},indent=2)+"\n")
prior=HERE.parent/"kernel450/hardware-validation.json"
regression=prior.exists() and json.loads(prior.read_text()).get("passed") is True
cacheproof_path=PRIVATE/"comparison-auditor-cache-validation.json"
cacheproof=json.loads(cacheproof_path.read_text()) if cacheproof_path.exists() else None
cachepassed=bool(cacheproof and cacheproof["passed"] and cacheproof["duplicate_success_receipt_rejected"])
ready=handoff is not None and regression and cachepassed
if ready:
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode="w:gz") as archive:
        for name,path in files.items():
            archive.add(path,arcname=name)
    (work/"comparison-payload.tar.gz").write_bytes(buffer.getvalue())
report=dict(
    stage=451,window_id=window,offline_preparation_only=True,phone_accessed=False,
    remote_staged=False,launched=False,build_source_or_artifacts_modified=False,
    worker_python_syntax_passed=True,frames_per_segment=180,total_requested_frames=540,
    ext4_storage_guard_used_before_payload_reads=True,
    order=["A1-old","B-new","A2-old"],only_camera_payload_difference="camss_ipa_proxy",
    core_sha256=old_hash["libcamera.so.0.7.2"],ipa_sha256=old_hash["ipa_camss_vfe.so"],
    signature_sha256=old_hash["ipa_camss_vfe.so.sign"],
    old_proxy_sha256=old_hash["camss_ipa_proxy"],new_proxy_sha256=new_hash["camss_ipa_proxy"],
    factory443_profile_sha256=common["factory-s5kgw1-private.yaml"],
    exact_441_modules_reused=True,observer_used=False,live_proc_exe_hash_required=True,
    fresh_handoff_received=handoff is not None,baseline450_strict_regression_passed=regression,
    strict_unfiltered_auditor_cache_selfcheck_passed=cachepassed,
    ready_for_manual_stage=ready,payload_generated=ready,
    static_preparation_passed=True,hardware_validation_passed=False,passed=True,
)
(HERE/"comparison-plan-validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
