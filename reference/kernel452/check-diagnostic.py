"""Offline raw receipt, bounded monitor and FULL CSV audit; no device calls."""
from pathlib import Path
import argparse
import collections
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path("/mnt/e/edk2-samurai-out/kernel452")
TYPES = ["Start", "PoolReady", "RequestEnter", "NoFreeFull", "InternalTake", "FullQbufBegin",
         "FullQbufResult", "FullDq", "PixSof", "Pd10Dq", "StatsDq", "StatsDone", "WaitOlder",
         "WaitIpe", "WaitPd10", "IpeClaim", "IpeQueue", "ImageProcessed", "InternalReturn",
         "RequestComplete", "RequestAccepted", "StopBegin", "StopEnd"]
COLUMNS = ("number,mono_ns,epoch,request,buffer,hardware_ns,active_request,type,sof,request_sequence,"
           "last_sof,free_full,requests,waiting_full,coarse,histograms,statistics,associations,flags,status,outstanding_full")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def auditor():
    source = load(HERE.parent / "kernel443/frame-audit.py", "gst443diagnostic").source
    for old, new in [
        ("coarse_bytes=46080):", "coarse_bytes=46080,target=120,expected_result=0):"),
        ("assert len(frames)==120", "assert len(frames)==target"),
        ("assert 'bus-errors=0 result=0' in text", "assert f'bus-errors=0 result={expected_result}' in text"),
    ]:
        assert source.count(old) == 1
        source = source.replace(old, new)
    namespace = {"re": re}
    exec(compile(source, "strict-443-diagnostic-no-receipt-filter", "exec"), namespace)
    return namespace["audit_gst"], hashlib.sha256(source.encode()).hexdigest()


def samples(text):
    rows = [tuple(map(int, match)) for match in re.findall(
        r"GST_IMAGE frame=(\d+) width=(\d+) height=(\d+) bytes=(\d+) pts=(\d+) hash=(\d+) sequence=(\d+) wall-ns=(\d+)", text)]
    assert rows and [row[0] for row in rows] == list(range(len(rows)))
    assert all(row[1:4] == (1920, 1080, 3110400) and row[5] > 0 for row in rows)
    assert all(b[4] > a[4] and b[6] > a[6] and b[7] > a[7] for a, b in zip(rows, rows[1:]))
    gaps = [dict(after_sof=a[6], before_sof=b[6], missing=b[6] - a[6] - 1, frame=b[0])
            for a, b in zip(rows, rows[1:]) if b[6] > a[6] + 1]
    return rows, gaps


def parse_trace(text):
    assert len(text.encode()) <= 4 * 1024 * 1024
    lines = text.splitlines()
    assert lines and text.endswith("\n")
    match = re.fullmatch(r"# full-trace,version=1,capacity=(\d+),total=(\d+),retained=(\d+),overwritten=(\d+),first=(\d+),clock-errors=(\d+),q-underflows=(\d+)", lines[0])
    assert match
    capacity, total, retained, overwritten, first, clocks, underflows = map(int, match.groups())
    assert capacity == 8192 and total >= 3 and retained == min(total, capacity)
    assert overwritten == total - retained and first == total - retained + 1
    assert clocks == underflows == 0
    totals = {}
    for line in lines[1:24]:
        match = re.fullmatch(r"# total,(\d+),(\d+)", line)
        assert match
        kind, count = map(int, match.groups())
        assert kind not in totals and 0 <= kind < len(TYPES)
        totals[kind] = count
    assert set(totals) == set(range(23)) and sum(totals.values()) == total
    assert all(totals[kind] == 1 for kind in [0, 21, 22])
    assert lines[24] == COLUMNS and lines[-1] == f"# end,records={retained}"
    reader = csv.DictReader(lines[24:-1])
    assert reader.fieldnames == COLUMNS.split(",")
    records = []
    counts = collections.Counter()
    previous_ns = 0
    outstanding = None if overwritten else 0
    for raw in reader:
        assert set(raw) == set(COLUMNS.split(",")) and None not in raw.values()
        event = {key: int(value) for key, value in raw.items()}
        assert event["number"] == first + len(records)
        assert event["mono_ns"] >= previous_ns and event["mono_ns"] > 0 and event["epoch"] == 1
        previous_ns = event["mono_ns"]
        kind = event["type"]
        assert 0 <= kind < 23 and 0 <= event["flags"] <= 31
        assert all(event[key] >= 0 for key in COLUMNS.split(",") if key != "status")
        delta = 1 if kind == 6 and event["status"] == 0 else (-1 if kind == 7 else 0)
        if outstanding is not None:
            assert event["outstanding_full"] == outstanding + delta
        outstanding = event["outstanding_full"]
        counts[kind] += 1
        records.append(event)
    assert len(records) == retained and records[-1]["type"] == 22
    assert all(count <= totals[kind] for kind, count in counts.items())
    assert counts[21] == counts[22] == 1
    summary = dict(capacity=capacity, total=total, retained=retained, overwritten=overwritten,
                   first_number=first, retained_mono_start_ns=records[0]["mono_ns"],
                   retained_mono_end_ns=records[-1]["mono_ns"],
                   retained_span_seconds=round((records[-1]["mono_ns"] - records[0]["mono_ns"]) / 1e9, 6),
                   whole_session_event_counts={TYPES[kind]: count for kind, count in totals.items()},
                   retained_event_counts={TYPES[kind]: count for kind, count in counts.items()},
                   clock_errors=clocks, q_underflows=underflows, end_footer_complete=True,
                   outstanding_is_successful_qbuf_minus_dq_callbacks=True,
                   outstanding_positive_does_not_prove_hardware_buffer_available=True,
                   hardware_and_callback_timestamps_kept_separate=True, passed=True)
    return summary, records


def gap_evidence(gaps, records):
    if not gaps:
        return dict(gap_observed=False, diagnosis_complete=False, root_cause_proven=False,
                    meaning="No consumed sequence gap; diagnostic usability only")
    gap = gaps[0]
    successful_full = {row["sof"]: row for row in records if row["type"] == 7 and row["status"] == 0 and row["flags"] & 8}
    covered = gap["after_sof"] in successful_full and gap["before_sof"] in successful_full
    if covered:
        covered = successful_full[gap["after_sof"]]["number"] < successful_full[gap["before_sof"]]["number"]
    result = dict(gap_observed=True, first_gap=gap, adjacent_full_dq_anchors_retained=covered,
                  diagnosis_complete=covered, root_cause_proven=False, missing_sof_evidence=[])
    if not covered or gap["missing"] > 256:
        result.update(diagnosis_complete=False, meaning="Gap outside reliable tail anchors or exceeds bounded SOF analysis")
        return result
    before = successful_full[gap["after_sof"]]
    after = successful_full[gap["before_sof"]]
    bracket = [row for row in records if before["number"] <= row["number"] <= after["number"]]
    counts = collections.Counter(row["type"] for row in bracket)
    result["adjacent_full_callback_bracket"] = dict(
        mono_span_ms=round((after["mono_ns"] - before["mono_ns"]) / 1e6, 3),
        event_counts={TYPES[kind]: counts[kind] for kind in [2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 19, 20]},
        queue_snapshot_ranges={key: dict(minimum=min(row[key] for row in bracket), maximum=max(row[key] for row in bracket))
                               for key in ["free_full", "requests", "waiting_full", "coarse", "statistics", "associations", "outstanding_full"]},
        callbacks_with_ipe_active=sum(bool(row["flags"] & 2) for row in bracket),
        no_request_enter_in_bracket=counts[2] == 0,
        snapshots_are_callback_times_not_hardware_sof_instants=True,
        no_request_enter_does_not_identify_consumer_cause=True)
    for sof in range(gap["after_sof"] + 1, gap["before_sof"]):
        observed = [row for row in records if row["sof"] == sof]
        full = [row for row in observed if row["type"] == 7 and row["status"] == 0 and row["flags"] & 8]
        pairs = [row for row in observed if row["type"] in [15, 16]]
        item = dict(sof=sof, full_success_dq_present=bool(full),
                    pd10_dq_present=any(row["type"] == 9 for row in observed),
                    statistics_dq_present=any(row["type"] == 10 for row in observed),
                    ipe_claim_or_queue_present=bool(pairs),
                    wait_events=sorted({TYPES[row["type"]] for row in observed if row["type"] in [12, 13, 14]}))
        if full:
            item["meaning"] = "FULL callback observed; inspect subsequent ownership/queue latency"
            item["dq_to_first_ipe_mono_ms"] = round((pairs[0]["mono_ns"] - full[0]["mono_ns"]) / 1e6, 3) if pairs else None
        else:
            item["meaning"] = "No successful FULL DQ callback retained between adjacent FULL SOFs; hardware DMA versus driver delivery unresolved"
        result["missing_sof_evidence"].append(item)
    return result


def audit(root, residual):
    state = json.loads((root / "state.json").read_text())
    assert state["terminal"] and state["passed"] and not state["failure"]
    assert state["formal_modules_restored"] and state["services_restored"] and state["diagnostic_final_checks"]["passed"]
    assert not state["new_faults"] and state["taint_before"] == state["taint_after"] == 0
    assert state["diagnostic_observer_used"] is False
    plan = json.loads((root / "diagnostic-plan-private.json").read_text())
    handoff = json.loads((root / "handoff-private.json").read_text())
    assert plan["window_id"] == handoff["window_id"] == state["diagnostic_window_id"]
    assert handoff["fresh_preflight_verified"] is True
    assert state["diagnostic_charging_before"] == state["diagnostic_charging_after"] == handoff["charging"]
    external = json.loads(residual.read_text())
    assert external["terminal"] and external["passed"] and external["worker_exited"]
    assert external["window_id"] == plan["window_id"] and external["handoff_sha256"] == sha(root / "handoff-private.json")
    assert not external["residual_processes"] and not external["user_directory_exists"]
    assert external["current_final_checks"]["passed"]
    build = json.loads((HERE / "build-validation.json").read_text())
    hashes = {row["name"]: row["sha256"] for row in build["runtime_files"]}
    for name, relative in [("libcamera.so.0.7.2", "lib/libcamera.so.0.7.2"),
                           ("ipa_camss_vfe.so", "ipa/ipa_camss_vfe.so"),
                           ("ipa_camss_vfe.so.sign", "ipa/ipa_camss_vfe.so.sign"),
                           ("camss_ipa_proxy", "proxy/camss_ipa_proxy")]:
        assert plan["common_payload"][relative] == hashes[name]
    strict, strict_hash = auditor()
    rows = []
    physical = 0
    capacities = []
    for name, enabled in [("disabled-120", False), ("trace-window", True)]:
        case = root / name
        text = (case / "client.log").read_text()
        frames, gaps = samples(text)
        summary = state["diagnostic_cases"][name]
        assert summary["trace_enabled"] == enabled and summary["frames"] == len(frames)
        assert len(frames) >= 12 and (len(frames) == 120 if not enabled else len(frames) < 10000)
        monitor = json.loads((case / "monitor-private.json").read_text())
        identity = monitor["identity"]
        assert monitor["passed"] and monitor["consumed_frames"] == len(frames)
        assert monitor["whole_log_rereads"] == 0 and not monitor["conditions_observer_used"]
        assert monitor["maximum_read_bytes"] <= monitor["read_chunk_bound"] == 262144
        assert monitor["maximum_partial_bytes"] <= monitor["partial_line_bound"] == 8192
        assert monitor["backlog_bound"] == 4194304
        assert identity["passed"] and identity["uid"] == 10000 and identity["effective_capabilities"] == 0
        assert identity["application_pid"] != identity["ipa_pid"]
        assert identity["actual_ipa_exe"] == state["diagnostic_userroot"] + "/proxy/camss_ipa_proxy"
        assert identity["actual_ipa_exe_sha256"] == hashes["camss_ipa_proxy"]
        assert identity["core_sha256_verified_before_start"] == hashes["libcamera.so.0.7.2"]
        assert identity["actual_candidate_core_mapping"] and identity["actual_ipa_module_mapping"]
        assert identity["application_exe"] == state["diagnostic_userroot"] + "/gst-sustained"
        assert identity["application_sha256"] == plan["common_payload"]["gst-sustained"]
        if gaps:
            assert all(monitor["first_gap"][key] == gaps[0][key] for key in gaps[0])
        else:
            assert monitor["first_gap"] is None
        expected = 9 if enabled else 0
        assert summary["child_exit"] == expected and summary["exit_code"] == (1 if enabled else 0)
        row = strict(text, "s5kgw1", width=1920, height=1080, stride=1920,
                     coarse_bytes=261120, target=len(frames), expected_result=expected)
        assert row["source_delivered_successful_images"] == summary["ipe_completed"]
        assert row["queued_images"] == summary["ipe_completed"] + row["stop_aborted_queued_images"]
        physical += summary["ipe_completed"]
        assert f"exited=1 exit={expected} signalled=0" in text and "FIXTURE_RESTORATION result=0" in text
        assert re.findall(r"APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)", text) == [
            ("10000", "10000", "0000000000000000")]
        capacity = re.findall(r"CAPACITY_START epoch=1 tid=(\d+) status=0 reason=selected active=1 users=1 original=(\S+) selected=(\S+)", text)
        assert len(capacity) == 1
        tid, original, selected = capacity[0]
        capacities.append((original, selected))
        assert re.search(r"CAPACITY_STOP epoch=1 tid=" + tid + r" status=0 reason=restored active=0 users=0 original=" + re.escape(original) + " selected=" + re.escape(selected), text)
        allowed = {int(value) for value in selected.split(",")}
        executions = [tuple(map(int, match)) for match in re.findall(r"FOCUS_EXECUTION epoch=1 sof=(\d+) valid=1 .*cpu-before=(\d+) cpu-after=(\d+)", text)]
        consumed = {frame[6] for frame in frames}
        assert consumed <= {entry[0] for entry in executions}
        assert all(before in allowed and after in allowed for sof, before, after in executions if sof in consumed)
        exported = list((case / "captures").iterdir())
        assert not (case / "conditions.log").exists()
        if enabled:
            sent = monitor["stop_signal"]
            assert sent["passed"] and sent["via_pidfd"] and sent["signal"] == "SIGINT"
            assert sent["pid"] == identity["application_pid"] != sent["fixture_pid"]
            assert sent["start_ticks"] == identity["application_start_ticks"]
            assert sent["exe"] == identity["application_exe"] and sent["executable_sha256"] == identity["application_sha256"]
            assert sent["uid"] == 10000 and sent["effective_capabilities"] == 0
            assert 0 < sent["sent_ns"] - monitor["launched_ns"] <= 90.5 * 10**9
            if monitor["stop_reason"] == "first_consumed_sequence_gap_plus_2s":
                assert gaps
                delay = sent["sent_ns"] - monitor["first_gap"]["detected_ns"]
                assert 2 * 10**9 <= delay <= 2.5 * 10**9
                assert 0 <= monitor["first_gap"]["detected_ns"] - monitor["first_gap"]["consumed_wall_ns"] <= 10**9
            else:
                assert monitor["stop_reason"] == "90s_bound"
                assert sent["sent_ns"] - monitor["launched_ns"] >= 90 * 10**9
            assert len(exported) == 1 and exported[0].suffix == ".csv" and not exported[0].is_symlink()
            export_proof = summary["trace_export"]
            assert export_proof["file"] == exported[0].name and export_proof["sha256"] == sha(exported[0])
            assert export_proof["bytes"] == exported[0].stat().st_size
            assert export_proof["uid"] == 10000 and export_proof["mode"] == 0o600
            assert export_proof["normal_stop_footer_present"] and export_proof["exporter_result"] == 0
            trace, records = parse_trace(exported[0].read_text())
            log = re.findall(r"FULL_OWNERSHIP_TRACE epoch=1 file=(\S+) total=(\d+) retained=(\d+) overwritten=(\d+) result=(-?\d+)", text)
            assert log == [(exported[0].name, str(trace["total"]), str(trace["retained"]), str(trace["overwritten"]), "0")]
            assert text.index("FULL_OWNERSHIP_TRACE ") < text.index("GST_RESULT ")
            row.update(trace=trace, diagnosis=gap_evidence(gaps, records), stop_reason=monitor["stop_reason"])
        else:
            assert not exported and "FULL_OWNERSHIP_TRACE " not in text
            assert monitor["stop_signal"] is None and monitor["stop_reason"] is None
            assert summary["trace_export"] is None
        row.update(name=name, consumed_sequence_gaps=gaps, raw_strict_receipts_passed=True,
                   capacity_restored=True, actual_old_proxy_verified=True,
                   application_fd_count_is_one_live_snapshot_not_a_leak_test=True)
        rows.append(row)
    assert capacities[0] == capacities[1]
    final = state["candidate_final_status"]
    assert final["jobs"] == final["completed"] == final["direct_completed"] == physical
    assert not any(final[key] for key in ["failed", "cancelled", "first_error", "fatal", "pinned", "orphans", "users", "running"])
    return dict(stage=452, window_id=plan["window_id"], rows=rows,
                physical_ipe_completed=physical, strict_auditor_sha256=strict_hash,
                receipt_filter_used=False, formal_and_charging_restored=True,
                external_worker_exit_and_no_residual_verified=True,
                diagnostic_usability_passed=True, root_cause_proven=False,
                exact449_state_null_path_csv_stopend_idle_and_normal_exit_verified=True,
                no_gap_means_usability_only=True, zero_drop_30fps_acceptance=False, passed=True)


def synthetic_csv(total=9000):
    events = []
    totals = collections.Counter()
    for number in range(1, total + 1):
        kind = 0 if number == 1 else (21 if number == total - 1 else (22 if number == total else 2))
        totals[kind] += 1
        values = [number, number * 1000, 1, 0, 0, 0, 0, kind, 4294967295, 4294967295,
                  4294967295, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        events.append(",".join(map(str, values)))
    retained = min(8192, total)
    lines = [f"# full-trace,version=1,capacity=8192,total={total},retained={retained},overwritten={total-retained},first={total-retained+1},clock-errors=0,q-underflows=0"]
    lines += [f"# total,{kind},{totals[kind]}" for kind in range(23)]
    lines += [COLUMNS, *events[-retained:], f"# end,records={retained}"]
    return "\n".join(lines) + "\n"


def self_check():
    from unittest.mock import patch
    body = load(HERE / "capture-body-diagnostic.py", "diagnosticbody")
    tail = body.Tail()
    content = "APPLICATION_PROCESS pid=123\nIPA stats pid=456\n"
    for frame, sof in enumerate([100, 101, 103, 104]):
        content += f"GST_IMAGE frame={frame} width=1920 height=1080 bytes=3110400 pts={frame+1} hash=1 sequence={sof} wall-ns={frame+1}\n"
    raw = content.encode()
    for index in range(0, len(raw), 17):
        tail.feed(raw[index:index+17], 10**9)
    assert tail.frames == 4 and tail.app == 123 and tail.ipa == 456 and not tail.partial
    assert tail.first_gap["after_sof"] == 101 and tail.first_gap["before_sof"] == 103 and tail.first_gap["missing"] == 1
    assert body.stop_due(dict(detected_ns=10**9), 3 * 10**9 - 1, 90 * 10**9) is None
    assert body.stop_due(dict(detected_ns=10**9), 3 * 10**9, 90 * 10**9) == "first_consumed_sequence_gap_plus_2s"
    assert body.stop_due(dict(detected_ns=89 * 10**9), 90 * 10**9, 90 * 10**9) == "90s_bound"
    assert body.stop_due(None, 90 * 10**9, 90 * 10**9) == "90s_bound"
    identity = dict(application_pid=123, application_start_ticks=456,
                    application_exe="/run/user/10000/k450-user-test/gst-sustained", application_sha256="digest")
    fake = dict(proc_identity=lambda pid: (Path("/proc") / str(pid), 456, {}), sha=lambda path: "digest")
    with patch.object(body, "common", return_value=fake), patch.object(body.os, "readlink", return_value=identity["application_exe"]), \
         patch.object(body.os, "pidfd_open", return_value=99) as opened, patch.object(body.os, "close") as closed, \
         patch.object(body.signal, "pidfd_send_signal") as signalled:
        result = body.verified_sigint("unused", identity, 999)
        assert result["via_pidfd"] and opened.call_args.args == (123, 0)
        assert signalled.call_count == closed.call_count == 1
        signal_rejections = 0
        for bad, fixture in [(identity, 123), (dict(identity, application_start_ticks=457), 999),
                             (dict(identity, application_exe="/another/exe"), 999),
                             (dict(identity, application_sha256="another-digest"), 999)]:
            try:
                body.verified_sigint("unused", bad, fixture)
            except AssertionError:
                signal_rejections += 1
        fake["proc_identity"] = lambda pid: (Path("/proc") / str(pid), next(changing), {})
        changing = iter([456, 457])
        try:
            body.verified_sigint("unused", identity, 999)
        except AssertionError:
            signal_rejections += 1
        assert signal_rejections == 5 and signalled.call_count == 1 and closed.call_count == 2
    negatives = 0
    for malformed in [b"x" * (body.MAX_PARTIAL_BYTES + 1), b"x" * (body.READ_BYTES + 1)]:
        try:
            body.Tail().feed(malformed, 1)
        except AssertionError:
            negatives += 1
    data = synthetic_csv()
    trace, records = parse_trace(data)
    assert (trace["retained"], trace["overwritten"], trace["first_number"]) == (8192, 808, 809)
    for malformed in [data.rsplit("# end", 1)[0], data.replace("clock-errors=0", "clock-errors=1"),
                      data.replace("q-underflows=0", "q-underflows=1"),
                      data.replace("overwritten=808", "overwritten=807"),
                      data.replace("809,809000,", "810,809000,", 1)]:
        try:
            parse_trace(malformed)
        except AssertionError:
            negatives += 1
    assert negatives == 7
    assert not gap_evidence([], records)["root_cause_proven"]
    assert not gap_evidence([dict(after_sof=1, before_sof=3, missing=1, frame=1)], records)["diagnosis_complete"]
    anchored = [dict(records[0], number=i + 1, mono_ns=(i + 1) * 1000, type=kind, sof=sof, status=0, flags=8)
                for i, (kind, sof) in enumerate([(7, 1), (9, 2), (10, 2), (7, 3)])]
    example = gap_evidence([dict(after_sof=1, before_sof=3, missing=1, frame=1)], anchored)
    assert example["diagnosis_complete"] and not example["root_cause_proven"]
    assert not example["missing_sof_evidence"][0]["full_success_dq_present"]
    assert example["missing_sof_evidence"][0]["pd10_dq_present"] and example["missing_sof_evidence"][0]["statistics_dq_present"]
    strict, strict_hash = auditor()
    cache_rows = []
    for stage, attempt, name, expected in [(450, "r2", "user-cancel-1080", 9), (450, "r3", "user-sustained-1080", 0)]:
        path = PRIVATE.parent / f"kernel{stage}/runtime-collected-{attempt}/{name}/client.log"
        text = path.read_text()
        frames, _ = samples(text)
        result = strict(text, "s5kgw1", width=1920, height=1080, stride=1920, coarse_bytes=261120,
                        target=len(frames), expected_result=expected)
        receipt = next(line for line in text.splitlines() if "IPE_RECEIPT " in line and "success=1 " in line)
        rejected = False
        try:
            strict(text.replace(receipt, receipt + "\n" + receipt, 1), "s5kgw1", width=1920, height=1080,
                   stride=1920, coarse_bytes=261120, target=len(frames), expected_result=expected)
        except AssertionError:
            rejected = True
        assert rejected
        cache_rows.append(dict(frames=len(frames), expected_result=expected,
                               source_completed=result["source_delivered_successful_images"], duplicate_success_receipt_rejected=True))
    return dict(stage=452, phone_accessed=False, synthetic_only_csv=True,
                bounded_tail_split_line_and_first_gap_passed=True, malformed_cases_rejected=negatives,
                stop_2s_and_90s_boundaries_passed=True, pidfd_signal_mock_only=True,
                unsafe_signal_cases_rejected=signal_rejections,
                callback_bracket_evidence_without_hardware_causality_passed=True,
                tail8192_overwritten808_passed=True, raw_unfiltered_cached_audits=cache_rows,
                strict_auditor_sha256=strict_hash, check_script_sha256=sha(HERE / "check-diagnostic.py"),
                capture_body_sha256=sha(HERE / "capture-body-diagnostic.py"), passed=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--residual", type=Path)
    args = parser.parse_args()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if args.self_check:
        result = self_check()
        path = PRIVATE / "diagnostic-offline-validation.json"
    else:
        assert args.root and args.residual
        result = audit(args.root, args.residual)
        path = PRIVATE / "diagnostic-hardware-validation.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
