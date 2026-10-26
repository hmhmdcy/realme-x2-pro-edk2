"""452 phone-side definitions. Importing performs no device operations."""
from pathlib import Path
import hashlib
import json
import os
import pwd
import re
import runpy
import shutil
import signal
import subprocess
import time

COMMON = None
READ_BYTES = 256 * 1024
MAX_PARTIAL_BYTES = 8192
MAX_BACKLOG_BYTES = 4 * 1024 * 1024


def common(root):
    global COMMON
    if COMMON is None:
        COMMON = runpy.run_path(str(Path(root) / "capture-common-private.py"))
    return COMMON


def validate_handoff(root, state):
    return common(root)["validate_handoff"](root, state)


def finalize(root, state):
    return common(root)["finalize"](root, state)


class Tail:
    """A forward cursor, bounded chunk/partial line, no growing line history."""
    def __init__(self):
        self.offset = 0
        self.partial = b""
        self.app = None
        self.ipa = None
        self.frames = 0
        self.previous = None
        self.first_gap = None
        self.max_read = 0
        self.max_partial = 0
        self.bytes_read = 0

    def feed(self, data, now_ns):
        assert len(data) <= READ_BYTES
        self.max_read = max(self.max_read, len(data))
        self.bytes_read += len(data)
        lines = (self.partial + data).split(b"\n")
        self.partial = lines.pop()
        self.max_partial = max(self.max_partial, len(self.partial))
        assert len(self.partial) <= MAX_PARTIAL_BYTES, "Oversized partial log line"
        for raw in lines:
            assert len(raw) <= MAX_PARTIAL_BYTES, "Oversized complete log line"
            line = raw.decode(errors="replace")
            for field, pattern in [("app", r"APPLICATION_PROCESS pid=(\d+)"),
                                   ("ipa", r"IPA stats pid=(\d+)")]:
                match = re.search(pattern, line)
                if match:
                    pid = int(match[1])
                    assert getattr(self, field) in (None, pid)
                    setattr(self, field, pid)
            match = re.fullmatch(
                r"GST_IMAGE frame=(\d+) width=1920 height=1080 bytes=3110400 "
                r"pts=(\d+) hash=(\d+) sequence=(\d+) wall-ns=(\d+)", line)
            if not match:
                continue
            frame, pts, digest, sof, wall_ns = map(int, match.groups())
            assert frame == self.frames and digest > 0
            if self.previous:
                previous_sof, previous_pts, previous_wall = self.previous
                assert sof > previous_sof and pts > previous_pts and wall_ns > previous_wall
                if sof > previous_sof + 1 and self.first_gap is None:
                    self.first_gap = dict(after_sof=previous_sof, before_sof=sof,
                                          missing=sof - previous_sof - 1, frame=frame,
                                          consumed_wall_ns=wall_ns, detected_ns=now_ns)
            self.previous = (sof, pts, wall_ns)
            self.frames += 1

    def read(self, handle, now_ns):
        size = os.fstat(handle.fileno()).st_size
        assert self.offset <= size and size - self.offset <= MAX_BACKLOG_BYTES, "Monitor backlog exceeded bound"
        data = handle.read(READ_BYTES)
        self.offset += len(data)
        self.feed(data, now_ns)
        return len(data)


def witness(root, userroot, tail, plan):
    helpers = common(root)
    started = time.monotonic_ns()
    assert tail.app and tail.ipa and tail.app != tail.ipa
    app, app_start, _ = helpers["proc_identity"](tail.app)
    ipa, ipa_start, _ = helpers["proc_identity"](tail.ipa)
    app_exe = os.readlink(app / "exe")
    assert app_exe == str(userroot / "gst-sustained")
    assert helpers["sha"](app / "exe") == plan["common_payload"]["gst-sustained"]
    core = str(userroot / "lib/libcamera.so.0.7.2")
    module = str(userroot / "ipa/ipa_camss_vfe.so")
    assert core in (app / "maps").read_text()
    maps = (ipa / "maps").read_text()
    assert core in maps and module in maps
    proxy_exe = os.readlink(ipa / "exe")
    assert proxy_exe == str(userroot / "proxy/camss_ipa_proxy")
    assert helpers["sha"](ipa / "exe") == plan["common_payload"]["proxy/camss_ipa_proxy"]
    assert helpers["proc_identity"](tail.app)[1] == app_start
    assert helpers["proc_identity"](tail.ipa)[1] == ipa_start
    return dict(application_pid=tail.app, application_start_ticks=app_start,
                application_exe=app_exe, application_sha256=helpers["sha"](app / "exe"),
                ipa_pid=tail.ipa, ipa_start_ticks=ipa_start, actual_ipa_exe=proxy_exe,
                actual_ipa_exe_sha256=plan["common_payload"]["proxy/camss_ipa_proxy"],
                core_sha256_verified_before_start=plan["common_payload"]["lib/libcamera.so.0.7.2"],
                actual_candidate_core_mapping=True, actual_ipa_module_mapping=True,
                uid=10000, effective_capabilities=0,
                application_fd_count_at_witness=len(list((app / "fd").iterdir())),
                witness_started_ns=started, witness_finished_ns=time.monotonic_ns(), passed=True)


def verified_sigint(root, identity, fixture_pid):
    """Never signal the fixture, process group, reused PID, or another executable."""
    helpers = common(root)
    pid = identity["application_pid"]
    assert pid != fixture_pid
    assert hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal")
    path, start, _ = helpers["proc_identity"](pid)
    assert start == identity["application_start_ticks"]
    assert os.readlink(path / "exe") == identity["application_exe"]
    assert helpers["sha"](path / "exe") == identity["application_sha256"]
    descriptor = os.pidfd_open(pid, 0)
    try:
        # Recheck after pidfd_open; the signal then targets this exact process.
        assert helpers["proc_identity"](pid)[1] == start
        assert os.readlink(path / "exe") == identity["application_exe"]
        when = time.monotonic_ns()
        signal.pidfd_send_signal(descriptor, signal.SIGINT, None, 0)
    finally:
        os.close(descriptor)
    return dict(pid=pid, start_ticks=start, exe=identity["application_exe"],
                executable_sha256=identity["application_sha256"], uid=10000,
                effective_capabilities=0, signal="SIGINT", via_pidfd=True,
                sent_ns=when, fixture_pid=fixture_pid, passed=True)


def stop_due(first_gap, now_ns, deadline_ns):
    if first_gap and now_ns >= first_gap["detected_ns"] + 2 * 10**9:
        return "first_consumed_sequence_gap_plus_2s"
    if now_ns >= deadline_ns:
        return "90s_bound"
    return None


def monitor(root, logfile, child, userroot, plan, trace_enabled, launched_ns):
    tail = Tail()
    identity = None
    sent = None
    stop_reason = None
    deadline_ns = launched_ns + 90 * 10**9
    with Path(logfile).open("rb", buffering=0) as handle:
        while child.poll() is None:
            now = time.monotonic_ns()
            tail.read(handle, now)
            if identity is None and tail.app and tail.ipa:
                identity = witness(root, userroot, tail, plan)
            if trace_enabled and sent is None:
                due = stop_due(tail.first_gap, now, deadline_ns)
                if due:
                    assert identity, "Cannot safely identify GST application for cancellation"
                    stop_reason = due
                    sent = verified_sigint(root, identity, child.pid)
            if trace_enabled and now > deadline_ns + 15 * 10**9:
                raise TimeoutError("GST/fixture exceeded normal cancellation grace; keep evidence, no blind kill")
            if not trace_enabled and now > launched_ns + 40 * 10**9:
                raise TimeoutError("Default-disabled short case exceeded fixture grace")
            time.sleep(.1)
        while tail.read(handle, time.monotonic_ns()):
            pass
    assert not tail.partial, "Incomplete final log line"
    assert identity and identity["passed"]
    if trace_enabled:
        assert sent and stop_reason, "Trace case ended before the intended bounded cancellation"
    return dict(identity=identity, stop_signal=sent, stop_reason=stop_reason,
                first_gap=tail.first_gap, consumed_frames=tail.frames,
                read_chunk_bound=READ_BYTES, partial_line_bound=MAX_PARTIAL_BYTES,
                backlog_bound=MAX_BACKLOG_BYTES, maximum_read_bytes=tail.max_read,
                maximum_partial_bytes=tail.max_partial, bytes_read=tail.bytes_read,
                whole_log_rereads=0, conditions_observer_used=False,
                launched_ns=launched_ns, finished_ns=time.monotonic_ns(), passed=True)


def run_diagnostic(root, state, save, status, idle, core):
    root = Path(root)
    plan = json.loads((root / "diagnostic-plan-private.json").read_text())
    helpers = common(root)
    assert [case["name"] for case in plan["cases"]] == ["disabled-120", "trace-window"]
    state["captures"] = {}
    state["diagnostic_cases"] = {}
    state["diagnostic_observer_used"] = False
    account = pwd.getpwuid(10000)
    nodes = [p for p in Path("/sys/class/video4linux").glob("v4l-subdev*")
             if (p / "name").read_text().startswith("s5kgw1 ")]
    devices = [p for p in Path("/sys/bus/i2c/drivers/s5kgw1").iterdir() if (p / "of_node").exists()]
    assert len(nodes) == len(devices) == 1
    camera_id = "/base" + str((devices[0] / "of_node").resolve()).split("/base", 1)[1]
    userroot = Path("/run/user/10000") / ("k450-user-" + root.name)
    state["diagnostic_userroot"] = str(userroot)
    for specification in plan["cases"]:
        name = specification["name"]
        enabled = specification["trace_enabled"]
        case = root / name
        case.mkdir()
        assert not userroot.exists() and not helpers["related"](userroot)
        userroot.mkdir(mode=0o700)
        child = None
        monitored = None
        try:
            for folder in ["lib", "ipa", "proxy", "captures"]:
                (userroot / folder).mkdir(mode=0o700)
            for relative, digest in plan["common_payload"].items():
                target = userroot / relative
                shutil.copyfile(root / relative, target)
                target.chmod(0o700 if relative in ["gst-sustained", "proxy/camss_ipa_proxy"] else 0o600)
                assert helpers["sha"](target) == digest
            for library in ["libcamera", "libcamera-base"]:
                (userroot / f"lib/{library}.so.0.7").symlink_to(f"{library}.so.0.7.2")
            for path in [userroot, *userroot.rglob("*")]:
                if path.is_symlink():
                    os.lchown(path, 10000, account.pw_gid)
                else:
                    os.chown(path, 10000, account.pw_gid)
            assert (userroot / "captures").stat().st_uid == 10000
            env = dict(os.environ)
            for variable in list(env):
                if variable == "LD_LIBRARY_PATH" or variable.startswith(("LIBCAMERA_", "CAPTURE_", "GST_")):
                    env.pop(variable, None)
            env.update(LIBCAMERA_LOG_LEVELS="*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG",
                       LD_LIBRARY_PATH=str(userroot / "lib"),
                       LIBCAMERA_IPA_MODULE_PATH=str(userroot / "ipa"),
                       LIBCAMERA_IPA_PROXY_PATH=str(userroot / "proxy"),
                       LIBCAMERA_CAMSS_VFE_PROFILE=str(userroot / "factory-s5kgw1-private.yaml"),
                       LIBCAMERA_IPA_FORCE_ISOLATION="1", CAPTURE_DIR=str(userroot / "captures"),
                       PIPELINE_FIXTURE_TIMEOUT_SECONDS="95" if enabled else "25",
                       GST_TARGET_FRAMES="10000" if enabled else "120",
                       GST_SENSOR_NODE="/dev/" + nodes[0].name)
            if enabled:
                env["LIBCAMERA_CAMSS_FULL_TRACE_DIR"] = str(userroot / "captures")
            assert ("LIBCAMERA_CAMSS_FULL_TRACE_DIR" in env) == enabled
            completed_before = status()["completed"]
            launched_ns = time.monotonic_ns()
            logfile = case / "client.log"
            with logfile.open("xb") as output:
                child = subprocess.Popen(
                    [str(root / "pipeline-fixture"), "/dev/media0", str(root / "user-launcher.py"),
                     str(userroot), "gst-sustained", camera_id, "1920", "1080"],
                    env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                    start_new_session=True)
                save("capture-" + name, client_pid=child.pid)
                monitored = monitor(root, logfile, child, userroot, plan, enabled, launched_ns)
                (case / "monitor-private.json").write_text(json.dumps(monitored, indent=2) + "\n")
                code = child.wait(timeout=1)
            text = logfile.read_text(errors="replace")
            expected = 9 if enabled else 0
            assert code == (1 if enabled else 0)
            assert f"exited=1 exit={expected} signalled=0" in text
            assert "FIXTURE_RESTORATION result=0" in text
            assert re.findall(r"APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)", text) == [
                ("10000", "10000", "0000000000000000")]
            results = re.findall(r"GST_RESULT frames=(\d+) width=1920 height=1080 bus-errors=0 result=(\d+)", text)
            assert len(results) == 1 and tuple(map(int, results[0])) == (monitored["consumed_frames"], expected)
            assert monitored["consumed_frames"] >= 12
            if not enabled:
                assert monitored["consumed_frames"] == 120
                assert "FULL_OWNERSHIP_TRACE " not in text
            idle()
            current = status()
            assert not any(current[key] for key in ["failed", "cancelled", "first_error", "fatal"])
            exports = list((userroot / "captures").iterdir())
            trace_export = None
            if enabled:
                assert len(exports) == 1 and exports[0].suffix == ".csv" and not exports[0].is_symlink()
                metadata = exports[0].stat()
                assert metadata.st_uid == 10000 and metadata.st_mode & 0o777 == 0o600
                raw = exports[0].read_bytes()
                assert len(raw) <= 4 * 1024 * 1024 and raw.endswith(b"\n")
                assert re.fullmatch(rb"# end,records=\d+", raw.splitlines()[-1])
                exported = re.findall(r"FULL_OWNERSHIP_TRACE epoch=1 file=(\S+) total=(\d+) retained=(\d+) overwritten=(\d+) result=(-?\d+)", text)
                assert len(exported) == 1 and exported[0][0] == exports[0].name and exported[0][-1] == "0"
                trace_export = dict(file=exports[0].name, sha256=hashlib.sha256(raw).hexdigest(),
                                    bytes=len(raw), uid=metadata.st_uid, mode=metadata.st_mode & 0o777,
                                    normal_stop_footer_present=True, exporter_result=0)
            else:
                assert not exports
            state["diagnostic_cases"][name] = dict(
                trace_enabled=enabled, frames=monitored["consumed_frames"],
                ipe_completed=current["completed"] - completed_before,
                exit_code=code, child_exit=expected, intentional_cancellation=enabled,
                live_proc_witness_passed=True, trace_export=trace_export,
                elapsed_seconds=round((time.monotonic_ns() - launched_ns) / 1e9, 3))
        finally:
            # Never target the fixture/process group. Its verified existing timeout
            # remains the last-resort normal SIGINT + restoration mechanism.
            if child is not None and child.poll() is None:
                child.wait(timeout=max(1, (launched_ns + 110 * 10**9 - time.monotonic_ns()) / 1e9))
            deadline = time.monotonic() + 6
            while helpers["related"](userroot) and time.monotonic() < deadline:
                time.sleep(.05)
            assert not helpers["related"](userroot), "Keep user directory; no blind process kill or unlink"
            captures = userroot / "captures"
            if captures.exists():
                for entry in captures.iterdir():
                    assert entry.is_file() and not entry.is_symlink() and entry.suffix == ".csv"
                    assert entry.stat().st_uid == 10000 and entry.stat().st_mode & 0o777 == 0o600
                shutil.copytree(captures, case / "captures")
            assert not userroot.is_symlink() and userroot.resolve().parent == Path("/run/user/10000").resolve()
            assert userroot.name == "k450-user-" + root.name
            shutil.rmtree(userroot)
    state["candidate_final_status"] = status()
    state["candidate_final_core"] = core()
