"""Offline preparation only: no SSH, stage, launch, SDK bind, or build."""
from pathlib import Path
import argparse
import ast
import hashlib
import io
import json
import struct
import sys
import tarfile
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
import storage
storage.mount.mounted_build()  # Before every ext4 source/build/payload read.
PRIVATE = Path("/mnt/e/edk2-samurai-out/kernel452")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", default="r1")
    parser.add_argument("--handoff", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    assert args.attempt.startswith("r") and args.attempt[1:].isdigit() and 1 <= int(args.attempt[1:]) <= 20
    assert bool(args.handoff) == bool(args.baseline)
    window = "k452-full-diagnostic-" + args.attempt
    work = PRIVATE / ("diagnostic-prepared-" + args.attempt)
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert not (work / "diagnostic-payload.tar.gz").exists(), "Do not overwrite an existing ready bundle"
    protected = ["source-state.json", "source-validation.json", "build-validation.json",
                 "full_ownership_trace.h", "0063-camss-bounded-full-ownership-trace.patch"]
    fingerprints = {name: sha(HERE / name) for name in protected}
    source = json.loads((HERE / "source-state.json").read_text())
    for row in source["source_hashes"]:
        assert sha(Path(source["source"]) / row["path"]) == row["sha256"]
    old = json.loads((HERE.parent / "kernel450/build-validation.json").read_text())
    new = json.loads((HERE / "build-validation.json").read_text())
    assert old["passed"] and new["passed"] and new["ipa_proxy_signature_preserved"]
    oldhash = {row["name"]: row["sha256"] for row in old["runtime_files"]}
    newhash = {row["name"]: row["sha256"] for row in new["runtime_files"]}
    assert oldhash["libcamera.so.0.7.2"] != newhash["libcamera.so.0.7.2"]
    assert all(oldhash[name] == newhash[name] for name in oldhash if name != "libcamera.so.0.7.2")
    inputs = json.loads((PRIVATE.parent / "kernel450/runtime-input-files-private.json").read_text())
    files = {}
    common_payload = {}
    for name, row in inputs.items():
        path = PRIVATE / "libcamera.so.0.7.2" if name == "lib/libcamera.so.0.7.2" else Path(row["path"])
        expected = newhash["libcamera.so.0.7.2"] if name == "lib/libcamera.so.0.7.2" else row["sha256"]
        assert sha(path) == expected
        files[name] = path
        common_payload[name] = expected
    assert common_payload["proxy/camss_ipa_proxy"] == oldhash["camss_ipa_proxy"]
    files.update({
        "factory-s5kgw1-private.yaml": PRIVATE.parent / "kernel443/factory-s5kgw1-private.yaml",
        "gst-sustained": PRIVATE.parent / "kernel449/gst-sustained",
        "pipeline-fixture": PRIVATE.parent / "kernel449/pipeline-fixture-long",
        "user-launcher.py": HERE.parent / "kernel450/user-launcher.py",
        "capture-body-diagnostic.py": HERE / "capture-body-diagnostic.py",
    })
    clients = json.loads((HERE.parent / "kernel449/long-client-build-validation.json").read_text())
    assert clients["passed"]
    for row in clients["clients"]:
        assert sha(files[row["name"]]) == row["sha256"]
        source_name = "gst-sustained.c" if row["name"] == "gst-sustained" else "pipeline-fixture-long.c"
        assert sha(HERE.parent / "kernel449" / source_name) == row["source_sha256"]
    for name in ["factory-s5kgw1-private.yaml", "gst-sustained"]:
        common_payload[name] = sha(files[name])
    modules = json.loads((HERE.parent / "kernel441/intree-build-validation.json").read_text())
    assert modules["passed"] and not modules["diagnostics"]
    module_proof = {}
    for row in modules["modules"]:
        if not row["runtime_candidate"]:
            continue
        path = Path(row["private_path"])
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
        shoff = struct.unpack_from("<Q", raw, 40)[0]
        stride, count, strings = struct.unpack_from("<HHH", raw, 58)
        sections = [struct.unpack_from("<IIQQQQIIQQ", raw, shoff + i * stride) for i in range(count)]
        names = raw[sections[strings][4]:sections[strings][4] + sections[strings][5]]
        note = next(section for section in sections if names[section[0]:].split(bytes([0]))[0] == b".note.gnu.build-id")
        filename = row["name"] + ".ko"
        files[filename] = path
        module_proof[row["name"].replace("-", "_")] = dict(
            file=filename, sha256=row["sha256"],
            note_sha256=hashlib.sha256(raw[note[4]:note[4] + note[5]]).hexdigest())

    # Exact frozen helper version; extract definitions only, no 451 runtime.
    helper_path = HERE.parent / "kernel451/capture-body-comparison.py"
    assert sha(helper_path) == "a65f6326fc2366e8bd0b225c1399c386d0aa86f83260d28e57e02ed04e279fff"
    helper = helper_path.read_text()
    helper = helper[:helper.index("def live_witness(")] + helper[helper.index("def finalize("):]
    helper = helper.replace("k451-proxy-comparison-", "k452-full-diagnostic-").replace("comparison", "diagnostic")
    ast.parse(helper)
    (work / "capture-common-private.py").write_text(helper)
    files["capture-common-private.py"] = work / "capture-common-private.py"

    handoff = None
    if args.handoff:
        handoff = json.loads(args.handoff.read_text())
        assert handoff["schema"] == "samurai-camera-handoff-v1"
        assert handoff["window_id"] == window and handoff["window_owner"] == "camera"
        assert handoff["fresh_preflight_verified"] is True and handoff["issued_at_utc"]
        assert handoff["formal_baseline_sha256"] == sha(args.baseline)
        assert len(handoff["formal_library_sha256"]) == 64 and Path(handoff["boot_guard_path"]).is_absolute()
        assert set(handoff["charging"]) == {
            "manifest_sha256", "notes", "limits", "source_type", "source_budget_ua",
            "native_udc_allowance_ua", "gadget_maxpower_ma", "service_enabled", "native_retained", "control_enabled"}
        files["handoff-private.json"] = args.handoff
        files["baseline-private.json"] = args.baseline
    proof = dict(modules=module_proof, boot_guard=handoff["boot_guard_path"] if handoff else "FRESH_HANDOFF_REQUIRED")
    (work / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    files["proof.json"] = work / "proof.json"
    plan = dict(stage=452, window_id=window, kernel_release=modules["modules"][0]["vermagic"].split()[0],
                common_payload=common_payload, isolated=True, width=1920, height=1080,
                cases=[dict(name="disabled-120", trace_enabled=False, target_frames=120),
                       dict(name="trace-window", trace_enabled=True, target_frames_safety_ceiling=10000,
                            max_monitor_seconds=90, first_gap_followup_seconds=2)],
                trace_capacity=8192, trace_event_bytes=112, trace_memory_bytes=917504,
                fixture_safety_seconds=95, fixture_normal_cancel_child_exit=9,
                monitor_read_bytes=256 * 1024, monitor_partial_bytes=8192, monitor_backlog_bytes=4 * 1024 * 1024,
                monitor_poll_seconds=.1, observer_used=False, only_camera_change_from450="libcamera.so.0.7.2",
                old444_proxy_preserved=True, no_fixed_9000_capture=True,
                existing_gst_state_null_cleanup_source_verified=True,
                fresh_handoff_required=True, automatic_stage_or_launch=False)
    (work / "diagnostic-plan-private.json").write_text(json.dumps(plan, indent=2) + "\n")
    files["diagnostic-plan-private.json"] = work / "diagnostic-plan-private.json"
    prefix = (HERE.parent / "kernel342/native-install.py").read_text().split("def versions():", 1)[0]
    prefix = prefix.replace("'stage':342", "'stage':452") + "\nimport runpy\n"
    body = (HERE.parent / "kernel434/capture-worker-body.py").read_text()
    start = body.index(" state['captures']={}")
    end = body.index("\nexcept BaseException:", start)
    body = body[:start] + " diagnostic['run_diagnostic'](root,state,save,status,idle,core)\n verified=True\n" + body[end:]
    needle = "try:\n assert Path('/proc/sys/kernel/random/boot_id')"
    assert body.count(needle) == 1
    body = body.replace(needle, "diagnostic=runpy.run_path(str(root/'capture-body-diagnostic.py'))\ntry:\n diagnostic['validate_handoff'](root,state)\n assert Path('/proc/sys/kernel/random/boot_id')")
    start = body.index("  if child is not None and child.poll() is None:")
    end = body.index("  if changed:", start)
    body = body[:start] + "  assert child is None, 'Diagnostic owns its local fixture and never blind-signals it'\n" + body[end:]
    needle = "  state['after_status']=status();state['after_core']=core();assert released(core())"
    assert body.count(needle) == 1
    body = body.replace(needle, needle + "\n  state['diagnostic_final_checks']=diagnostic['finalize'](root,state)")
    worker = prefix + body
    assert "os.killpg" not in worker
    ast.parse(worker)
    (work / "worker.py").write_text(worker)
    files["worker.py"] = work / "worker.py"

    # Only render independent inspect/collect code. Neither is executed here.
    observer_path = HERE.parent / "kernel451/observe-comparison.py"
    assert sha(observer_path) == "3a5716a62b817fc355343c677de73e298c421644e9e02c7438c0e58289f3fe50"
    tree = ast.parse(observer_path.read_text())
    remote = next(ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "REMOTE" for t in node.targets))
    digest = sha(args.handoff) if args.handoff else "FRESH_HANDOFF_REQUIRED"
    remote = remote.replace("capture-body-comparison.py", "capture-body-diagnostic.py")
    remote = remote.replace("state.get('sustained',{})", "state.get('diagnostic_cases',{})")
    remote = remote.replace("ROOT", repr("/var/lib/samurai/" + window)).replace("EXPECTED", repr(digest))
    ast.parse(remote)
    (work / "inspect-terminal-private.py").write_text(remote)
    collector = '''from pathlib import Path
import hashlib,json,sys,tarfile
root=Path(ROOT)
expected=EXPECTED
assert expected!='FRESH_HANDOFF_REQUIRED'
assert hashlib.sha256((root/'handoff-private.json').read_bytes()).hexdigest()==expected
handoff=json.loads((root/'handoff-private.json').read_text())
assert handoff['window_id']==root.name and handoff['window_owner']=='camera' and handoff['fresh_preflight_verified'] is True
assert Path(handoff['boot_guard_path']).read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert json.loads((root/'state.json').read_text())['terminal']
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',compresslevel=1) as archive:
 for path in root.rglob('*'):
  if path.is_file() and not path.is_symlink() and path.suffix in ['.csv','.log','.json','.txt']:
   assert path.stat().st_size<=64*1024*1024
   archive.add(path,arcname=str(path.relative_to(root)),recursive=False)
'''.replace("ROOT", repr("/var/lib/samurai/" + window)).replace("EXPECTED", repr(digest))
    ast.parse(collector)
    assert "'.csv'" in collector
    (work / "collect-private.py").write_text(collector)
    for name in ["prepare-diagnostic.py", "capture-body-diagnostic.py", "check-diagnostic.py"]:
        ast.parse((HERE / name).read_text())
    manifest = {name: sha(path) for name, path in files.items()}
    (work / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    files["manifest.json"] = work / "manifest.json"
    (work / "payload-files-private.json").write_text(json.dumps({name: str(path) for name, path in files.items()}, indent=2) + "\n")
    cache_path = PRIVATE / "diagnostic-offline-validation.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    cache_passed = bool(cache.get("passed") and cache.get("check_script_sha256") == sha(HERE / "check-diagnostic.py")
                        and cache.get("capture_body_sha256") == sha(HERE / "capture-body-diagnostic.py"))
    ready = handoff is not None and cache_passed
    if ready:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name, path in files.items():
                archive.add(path, arcname=name)
        (work / "diagnostic-payload.tar.gz").write_bytes(buffer.getvalue())
    assert fingerprints == {name: sha(HERE / name) for name in protected}
    report = dict(stage=452, window_id=window, offline_preparation_only=True,
                  phone_accessed=False, remote_staged=False, launched=False, rebuilt=False,
                  source_header_build_fingerprints_preserved=True, ext4_mount_guard_before_reads=True,
                  core_sha256=newhash["libcamera.so.0.7.2"], old_proxy_sha256=newhash["camss_ipa_proxy"],
                  ipa_sha256=newhash["ipa_camss_vfe.so"], signature_sha256=newhash["ipa_camss_vfe.so.sign"],
                  only_camera_change_from450="core452", default_disabled_short_frames=120,
                  trace_capacity=8192, monitor_max_seconds=90, gap_followup_seconds=2,
                  verified_application_pidfd_sigint_only=True, collector_accepts_csv=True,
                  scripts_and_rendered_worker_syntax_passed=True, offline_selfcheck_passed=cache_passed,
                  fresh_handoff_received=handoff is not None, ready_for_manual_stage=ready,
                  payload_generated=ready, hardware_validation_passed=False, passed=True)
    (HERE / "diagnostic-plan-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
