"""Strict cached A/B/A audit. No device calls, normalization or receipt filter."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import statistics
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PRIVATE=Path("/mnt/e/edk2-samurai-out/kernel451")

def auditor():
    spec=importlib.util.spec_from_file_location("gst443",HERE.parent/"kernel443/frame-audit.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=module.source
    assert source.count("coarse_bytes=46080):")==source.count("assert len(frames)==120")==1
    source=source.replace("coarse_bytes=46080):","coarse_bytes=46080,target=180):")
    source=source.replace("assert len(frames)==120","assert len(frames)==target")
    namespace={"re":re};exec(compile(source,"strict-443-variable-count-unfiltered","exec"),namespace)
    return namespace["audit_gst"],hashlib.sha256(source.encode()).hexdigest()

def quantiles(values):
    data=sorted(values)
    assert data
    return dict(n=len(data),median_ms=round(statistics.median(data),3),
                p95_ms=round(data[min(len(data)-1,len(data)*95//100)],3),
                p99_ms=round(data[min(len(data)-1,len(data)*99//100)],3),
                maximum_ms=round(data[-1],3))

def samples(text):
    rows=[tuple(map(int,match)) for match in re.findall(
        r"GST_IMAGE frame=(\d+) width=(\d+) height=(\d+) bytes=(\d+) pts=(\d+) hash=(\d+) sequence=(\d+) wall-ns=(\d+)",text)]
    assert rows and [row[0] for row in rows]==list(range(len(rows)))
    assert all(row[1:4]==(1920,1080,3110400) and row[5]>0 for row in rows)
    assert all(b[4]>a[4] and b[6]>a[6] and b[7]>a[7] for a,b in zip(rows,rows[1:]))
    return rows

def performance(text,frames,first):
    wanted={row[6] for row in frames[first:]}
    events={};dispatch={};focus={}
    stamp=re.compile(r"^\[(\d+):(\d+):(\d+)\.(\d{9})\]")
    for line in text.splitlines():
        when=stamp.match(line)
        if not when:
            continue
        fields=dict(re.findall(r"([a-z][a-z0-9-]*)=([^ ]+)",line))
        if "sof" not in fields or int(fields["sof"]) not in wanted:
            continue
        sof=int(fields["sof"]);h,m,s,ns=map(int,when.groups())
        ns=((h*60+m)*60+s)*10**9+ns
        entry=events.setdefault(sof,{})
        for label,marker in [
            ("af","AF frame "),("tone","IPE_TONE_PREPARE "),("tone","IPE_TONE_BOOTSTRAP "),
            ("tone","IPE_CCM_PREPARE "),("end","FRAME_IPA_PREPARE "),
            ("pair","IPE_PAIR "),("queue","IPE_TONE_QUEUE "),("receipt","IPE_RECEIPT "),
        ]:
            if marker in line and (label!="receipt" or fields["success"]=="1"):
                entry[label]=max(entry.get(label,0),ns)
        if "FRAME_IPA_PREPARE " in line:
            dispatch[sof]=int(fields["dispatch-us"])
        if "FOCUS_EXECUTION " in line:
            focus[sof]=(int(fields["sample-wall-us"]),int(fields["sample-cpu-us"]))
    assert set(dispatch)==set(focus)==wanted
    assert all({"af","tone","end","pair","queue","receipt"}<=set(events[sof]) for sof in wanted)
    gaps=[dict(after_sof=a[6],before_sof=b[6],missing=b[6]-a[6]-1)
          for a,b in zip(frames,frames[1:]) if b[6]>a[6]+1]
    steady=frames[first:]
    metrics={
        "focus_dispatch":quantiles([dispatch[sof]/1000 for sof in wanted]),
        "focus_sample_wall":quantiles([focus[sof][0]/1000 for sof in wanted]),
        "focus_sample_thread_cpu":quantiles([focus[sof][1]/1000 for sof in wanted]),
        "focus_off_cpu_approx":quantiles([max(0,focus[sof][0]-focus[sof][1])/1000 for sof in wanted]),
        "af_to_last_tone_log":quantiles([(events[sof]["tone"]-events[sof]["af"])/1e6 for sof in wanted]),
        "last_tone_log_to_host_return_log":quantiles([(events[sof]["end"]-events[sof]["tone"])/1e6 for sof in wanted]),
        "pair_to_queue":quantiles([(events[sof]["queue"]-events[sof]["pair"])/1e6 for sof in wanted]),
        "queue_to_receipt":quantiles([(events[sof]["receipt"]-events[sof]["queue"])/1e6 for sof in wanted]),
        "pts_intervals":quantiles([(b[4]-a[4])/1e6 for a,b in zip(steady,steady[1:])]),
    }
    return dict(steady_first_frame=first,steady_frames=len(steady),metrics=metrics,
                timestamp_fps=round((len(steady)-1)*1e9/(steady[-1][4]-steady[0][4]),3),
                whole_segment_missing_sofs=sum(row["missing"] for row in gaps),
                whole_segment_gaps=gaps,log_phase_intervals_are_not_worker_cpu_accounting=True)

def audit(root,residual):
    state=json.loads((root/"state.json").read_text())
    assert state["terminal"] and state["passed"] and not state["failure"]
    assert not state["new_faults"] and state["taint_after"]==state["taint_before"]==0
    assert state["formal_modules_restored"] and state["services_restored"]
    assert state["comparison_observer_used"] is False
    assert state["comparison_final_checks"]["passed"]
    plan=json.loads((root/"comparison-plan-private.json").read_text())
    handoff=json.loads((root/"handoff-private.json").read_text())
    assert plan["window_id"]==handoff["window_id"]==state["comparison_window_id"]
    assert state["comparison_charging_before"]==state["comparison_charging_after"]==handoff["charging"]
    assert handoff["fresh_preflight_verified"] is True
    observation=json.loads(residual.read_text())
    assert observation["terminal"] and observation["passed"] and observation["window_id"]==plan["window_id"]
    assert not observation["residual_processes"] and not observation["user_directory_exists"]
    assert observation["current_final_checks"]["passed"] and observation["worker_exited"]
    assert observation["handoff_sha256"]==hashlib.sha256((root/"handoff-private.json").read_bytes()).hexdigest()
    old=json.loads((HERE.parent/"kernel450/build-validation.json").read_text())
    new=json.loads((HERE/"build-validation.json").read_text())
    oldhash={row["name"]:row["sha256"] for row in old["runtime_files"]}
    newhash={row["name"]:row["sha256"] for row in new["runtime_files"]}
    assert plan["common_payload"]["lib/libcamera.so.0.7.2"]==oldhash["libcamera.so.0.7.2"]==newhash["libcamera.so.0.7.2"]
    expected=[oldhash["camss_ipa_proxy"],newhash["camss_ipa_proxy"],oldhash["camss_ipa_proxy"]]
    assert plan["common_payload"]["ipa/ipa_camss_vfe.so"]==oldhash["ipa_camss_vfe.so"]==newhash["ipa_camss_vfe.so"]
    assert plan["common_payload"]["ipa/ipa_camss_vfe.so.sign"]==oldhash["ipa_camss_vfe.so.sign"]==newhash["ipa_camss_vfe.so.sign"]
    assert [segment["name"] for segment in plan["segments"]]==["A1","B","A2"]
    assert [segment["proxy_sha256"] for segment in plan["segments"]]==expected and expected[0]!=expected[1]
    records=[]
    for segment in plan["segments"]:
        name=segment["name"];case=root/name
        witness=json.loads((case/"live-proxy-private.json").read_text())
        assert witness["passed"] and witness["uid"]==10000 and witness["effective_capabilities"]==0
        assert witness["application_pid"]!=witness["ipa_pid"]
        assert witness["actual_ipa_exe_sha256"]==segment["proxy_sha256"]
        assert witness["actual_ipa_exe"]==state["comparison_userroot"]+"/proxy/camss_ipa_proxy"
        assert witness["actual_candidate_core_mapping"] and witness["actual_ipa_module_mapping"]
        assert witness["core_sha256_verified_before_start"]==oldhash["libcamera.so.0.7.2"]
        assert witness["witness_finished_ns"]>=witness["witness_started_ns"]>0
        assert not (case/"conditions.log").exists()
        text=(case/"client.log").read_text()
        frames=samples(text);assert len(frames)==180
        records.append((segment,witness,text,frames))
    first=max(60,max(witness["last_consumed_frame_at_witness_end"]+8 for _,witness,_,_ in records))
    assert first<=120,"Live-witness work overlaps too much of the performance window"
    strict,source_hash=auditor();rows=[];physical=0;capacities=[]
    for segment,witness,text,frames in records:
        name=segment["name"];summary=state["sustained"][name]
        row=strict(text,"s5kgw1",width=1920,height=1080,stride=1920,coarse_bytes=261120,target=180)
        assert row["source_delivered_successful_images"]==summary["ipe_completed"]
        assert row["queued_images"]==summary["ipe_completed"]+row["stop_aborted_queued_images"]
        physical+=summary["ipe_completed"]
        assert summary["frames"]==180 and summary["exit_code"]==0 and summary["live_proc_witness_passed"]
        assert re.findall(r"APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)",text)==[
            ("10000","10000","0000000000000000")]
        assert "exited=1 exit=0 signalled=0" in text and "FIXTURE_RESTORATION result=0" in text
        starts=re.findall(r"CAPACITY_START epoch=1 tid=(\d+) status=0 reason=selected active=1 users=1 original=(\S+) selected=(\S+)",text)
        assert len(starts)==1
        tid,original,selected=starts[0];capacities.append((original,selected))
        assert re.search(r"CAPACITY_STOP epoch=1 tid="+tid+r" status=0 reason=restored active=0 users=0 original="+re.escape(original)+" selected="+re.escape(selected),text)
        assert frames[first][7]>witness["witness_finished_ns"]
        allowed={int(value) for value in selected.split(",")}
        execution=[tuple(map(int,match)) for match in re.findall(
            r"FOCUS_EXECUTION epoch=1 sof=(\d+) valid=1 .*cpu-before=(\d+) cpu-after=(\d+)",text)]
        consumed={frame[6] for frame in frames}
        assert consumed<={entry[0] for entry in execution}
        assert all(before in allowed and after in allowed for sof,before,after in execution if sof in consumed)
        row.update(name=name,kind=segment["kind"],raw_strict_receipts_passed=True,
                   capacity_restored=True,live_proxy_sha256=witness["actual_ipa_exe_sha256"],
                   performance=performance(text,frames,first))
        rows.append(row)
    assert capacities[0]==capacities[1]==capacities[2]
    final=state["candidate_final_status"]
    assert final["jobs"]==final["completed"]==final["direct_completed"]==physical
    assert not any(final[key] for key in ["failed","cancelled","first_error","fatal","pinned","orphans","users","running"])
    def metric(index,key,field="median_ms"):
        return rows[index]["performance"]["metrics"][key][field]
    comparison={}
    for key in rows[0]["performance"]["metrics"]:
        comparison[key]=dict(A1_median_ms=metric(0,key),B_median_ms=metric(1,key),A2_median_ms=metric(2,key),
                             B_minus_A1_median_ms=round(metric(1,key)-metric(0,key),3),
                             B_minus_A2_median_ms=round(metric(1,key)-metric(2,key),3))
    return dict(stage=451,window_id=plan["window_id"],rows=rows,comparison=comparison,
                consumed_frames=540,physical_ipe_completed=physical,steady_common_first_frame=first,
                strict_auditor_sha256=source_hash,all_live_proxy_exe_hashes_verified=True,
                core_ipa_signature_factory_and_modules_common=True,observer_used=False,
                formal_restoration_and_external_residual_passed=True,charging_before_after_equal=True,
                single_ABA_does_not_prove_drop_causality=True,thermal_or_power_acceptance=False,
                zero_drop_30fps_acceptance=False,passed=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path)
    parser.add_argument("--residual",type=Path)
    parser.add_argument("--self-check",type=Path)
    args=parser.parse_args()
    if args.self_check:
        text=args.self_check.read_text()
        rows=samples(text);strict,source_hash=auditor()
        positive=strict(text,"s5kgw1",width=1920,height=1080,stride=1920,coarse_bytes=261120,target=len(rows))
        measured=performance(text,rows,60)
        receipt=next(line for line in text.splitlines() if "IPE_RECEIPT " in line and "success=1 " in line)
        corrupted=text.replace(receipt,receipt+"\n"+receipt,1)
        rejected=False
        try:
            strict(corrupted,"s5kgw1",width=1920,height=1080,stride=1920,coarse_bytes=261120,target=len(rows))
        except AssertionError:
            rejected=True
        assert rejected
        result=dict(stage=451,cache_frames=positive["frames"],raw_unmodified_cache_passed=True,
                    duplicate_success_receipt_rejected=True,receipt_filter_used=False,
                    cached_performance_frames=measured["steady_frames"],
                    cached_performance_phase_parser_passed=True,
                    strict_auditor_sha256=source_hash,phone_accessed=False,passed=True)
        PRIVATE.mkdir(mode=0o700,exist_ok=True)
        (PRIVATE/"comparison-auditor-cache-validation.json").write_text(json.dumps(result,indent=2)+"\n")
    else:
        assert args.root and args.residual,"Full comparison audit requires collected root and fresh external terminal residual"
        result=audit(args.root,args.residual)
        (PRIVATE/"comparison-validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
