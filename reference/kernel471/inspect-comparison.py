"""Independent cached A/B/A audit.  Importing this module performs no I/O.

All three segments use the same 32-frame consumer and bounded FULL ring.
Timing intervals are wall-clock observations; no performance pass threshold is
defined and an absence of sequence gaps is not long-term acceptance.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CASES = ['A1-old', 'B-new', 'A2-old']
OLD = 'c7887708377b92b167d917173cb2840a78e437a773985fa087ef980bd382038c'
NEW = '35526054954ce43d1068c710f6be6d4cd172288e4da7ffcab677712815f08f4d'
CORE = '9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af'
IPA = '4c90047d42a91b9b1585d3b2cda997d8eee61f5e3a20f136b4345abcc2556d39'
PROFILE = '6396ced1039e352a14c7a07187e780596a3a4180b22391bca0b30f7518db4094'
CLIENT = '7f4d6a1f8527280d8bbe11e6af638348200bd9bc8465be8357cdc0ca732b852a'
SENSOR = '494910c99ef116b88038ac3dfcc020a90aa35bfcc610b6b37c152601ee758392'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modules():
    timing = load_module('timing470for471', HERE.parent / 'kernel470/analyze-cached.py')
    ring = load_module('ring452for471', HERE.parent / 'kernel452/check-diagnostic.py')
    guard = load_module('guard463for471', HERE.parent / 'kernel463/guarded-trace.py')
    original = load_module('strict443for471', HERE.parent / 'kernel443/frame-audit.py').source
    source = original
    for before, after in [("model=='s5kgw1'", "model=='s5k3m5'"),
                          ('assert len(frames)==120', 'assert len(frames)==32')]:
        assert source.count(before) == 1
        source = source.replace(before, after)
    namespace = {'re': re}
    exec(compile(source, 'strict443-tele32-471-unfiltered', 'exec'), namespace)
    return timing, ring, guard, namespace['audit_gst'], hashlib.sha256(source.encode()).hexdigest()


def metric(timing, pairs):
    return timing.summary([timing.delta(a, b) for a, b in pairs])


def one(events, predicate, context):
    found = [event for event in events if predicate(event)]
    assert len(found) == 1, (context, len(found))
    return found[0]


def inspect_case(case, expected_proxy, trace_events, full_role, summary, dependencies):
    timing, ring_reader, guard, strict, strict_sha = dependencies
    log = case / 'client.log'
    text = log.read_text()
    strict_result = strict(text, 's5k3m5', width=1920, height=1080, stride=1920, coarse_bytes=261120)
    assert strict_result['frames'] == 32
    assert strict_result['queued_images'] == summary['ipe_completed']
    samples = [tuple(map(int, row)) for row in re.findall(
        r'GST_IMAGE frame=(\d+) width=(\d+) height=(\d+) bytes=(\d+) pts=(\d+) hash=(\d+) sequence=(\d+) wall-ns=(\d+)', text)]
    assert len(samples) == 32 and [s[0] for s in samples] == list(range(32))
    assert all(s[1:4] == (1920, 1080, 3110400) and s[5] > 0 for s in samples)
    assert all(b[4] > a[4] and b[6] > a[6] and b[7] > a[7] for a, b in zip(samples, samples[1:]))
    assert re.findall(r'GST_SENSOR width=(\d+) height=(\d+) code=(\d+)', text) == [('4208', '2368', '12298')]
    assert re.findall(r'APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)', text) == [('10000', '10000', '0000000000000000')]
    assert 'FIXTURE_RESTORATION result=0' in text and 'exited=1 exit=0 signalled=0' in text
    assert re.search(r'CAPACITY_STOP epoch=1 .* reason=inactive active=0 users=0 ', text)
    assert 'CAPACITY_START ' not in text and 'FOCUS_TIMING ' not in text
    raw_receipts = re.findall(r'IPE_RECEIPT epoch=(\d+) sof=(\d+) token=(\d+) success=([01]) result=(-?\d+) trace=(\d+) pending=(\d+)', text)
    assert len(raw_receipts) == text.count('IPE_RECEIPT ')
    assert len({(r[0], r[2]) for r in raw_receipts}) == len(raw_receipts)
    assert all(r[3] == r[4] and r[4] in ['0', '1'] for r in raw_receipts)
    witness_file = case / 'live-witness-private.json'
    witness = json.loads(witness_file.read_bytes())
    assert witness['passed'] and witness['isolated'] and witness['application']['exe_sha256'] == CLIENT
    assert witness['core_mapping_verified'] and witness['actual_ipa_mapping_verified']
    assert witness['proxy_exe_sha256'] == expected_proxy
    assert {int(p) for p in re.findall(r'APPLICATION_PROCESS pid=(\d+)', text)} == {witness['application']['pid']}
    assert {int(p) for p in re.findall(r'IPA stats pid=(\d+)', text)} == {witness['ipa_pid']}
    guard.role.check_open_fd(full_role, witness['full_fd_observation'], witness['application'])
    csv_files = sorted((case / 'captures').glob('*.csv'))
    assert len(csv_files) == 1, (case.name, 'one bounded CSV required', len(csv_files))
    ring_summary, records = ring_reader.parse_trace(csv_files[0].read_text())
    assert ring_summary['overwritten'] == 0 and records[0]['type'] == 0
    assert ring_summary['whole_session_event_counts']['Start'] == 1
    export = re.findall(r'FULL_OWNERSHIP_TRACE epoch=(\d+) file=(\S+) total=(\d+) retained=(\d+) overwritten=(\d+) result=(-?\d+)', text)
    assert len(export) == 1
    epoch, filename, total, retained, overwritten, result = export[0]
    assert epoch == '1' and Path(filename).name == csv_files[0].name and result == '0'
    assert tuple(map(int, (total, retained, overwritten))) == tuple(ring_summary[k] for k in ['total', 'retained', 'overwritten'])
    logs, by_sof = timing.parse_log(text)
    low, high = min(e['ns'] for e in logs), max(e['ns'] for e in logs)
    assert low <= records[0]['mono_ns'] <= records[-1]['mono_ns'] <= high
    pipeline_tids = {int(p) for p in re.findall(r'\] \[(\d+)\] +(?:INFO|DEBUG|WARN|ERROR) CamssVfe ', text)}
    kernel_dq = [e for e in trace_events if e['kind'] == 'v4l2_dqbuf' and e.get('minor') == full_role['minor']
                 and low <= e['ns'] <= high]
    assert kernel_dq and all(e['pid'] in pipeline_tids for e in kernel_dq)
    kernel_ioctls = [e for e in trace_events if e['kind'] in ['v4l2_qbuf', 'v4l2_dqbuf']
                     and e.get('minor') == full_role['minor'] and low <= e['ns'] <= high]
    assert len(pipeline_tids) == 1 and all(e['pid'] in pipeline_tids for e in kernel_ioctls)
    cpu_histogram = {name: dict(sorted(collections.Counter(str(e['cpu']) for e in kernel_ioctls
                                                          if e['kind'] == name).items()))
                     for name in ['v4l2_qbuf', 'v4l2_dqbuf']}
    last_cpu = kernel_dq[-1]['cpu']
    tail = []
    for event in reversed(kernel_dq):
        if event['cpu'] != last_cpu:
            break
        tail.append(event)
    tail.reverse()
    ring_dq = [r for r in records if r['type'] == 7 and r['status'] == 0 and r['flags'] & 8]
    assert len({r['sof'] for r in ring_dq}) == len(ring_dq)
    linked = {}
    for row in ring_dq:
        d = one(kernel_dq, lambda e: e['sequence'] == row['sof']
                and e['timestamp'] == row['hardware_ns'] // 1000 * 1000
                and e['ns'] <= row['mono_ns'], ('ring/v4l2 FULL', case.name, row['sof']))
        vb = one(trace_events, lambda e: e['kind'] == 'vb2_dqbuf' and e['pid'] == d['pid']
                 and e['index'] == d['index'] and e['timestamp'] // 1000 * 1000 == d['timestamp']
                 and 0 <= d['ns'] - e['ns'] < 2_000_000, ('v4l2/vb2 FULL', case.name, row['sof']))
        linked[row['sof']] = dict(ring=row, kernel=d, vb2=vb)
    owners = {p['vb2']['owner'] for p in linked.values()}
    assert len(owners) == 1
    owner = next(iter(owners))
    owner_events = [e for e in trace_events if e.get('owner') == owner and low <= e['ns'] <= high]
    frame_rows = []
    lsc_applied, lsc_context = {}, {}
    for line in text.splitlines():
        values = dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)', line))
        if 'LSC_APPLIED ' in line:
            revision = int(values['revision'])
            assert revision not in lsc_applied
            lsc_applied[revision] = values
        if 'LSC_CONTEXT ' in line:
            sof = int(values['sof'])
            assert sof not in lsc_context
            lsc_context[sof] = values
    for sample in samples:
        sof = sample[6]
        pair = linked[sof]
        fdq = pair['ring']
        values = by_sof[sof]
        frame = dict(sof=sof, gst=sample[7], full_dq=fdq['mono_ns'], full_completion_timestamp=fdq['hardware_ns'])
        for name in ['IPE_PAIR', 'IPE_TONE_PREPARE', 'IPE_TONE_BOOTSTRAP', 'TONE_IPA_PREPARE', 'IPE_TONE_QUEUE', 'IPE_RECEIPT']:
            found = values.get(name, [])
            if found:
                assert len(found) == 1
                frame[name] = found[0]['ns']
        assert values['IPE_RECEIPT'][0]['success'] == '1'
        frame['dispatch_us'] = int(values['TONE_IPA_PREPARE'][0]['dispatch-us'])
        sof_event = one(records, lambda e: e['type'] == 8 and e['sof'] == sof, ('PixSof', case.name, sof))
        assert sof_event['hardware_ns'] > 0 and sof_event['hardware_ns'] <= sof_event['mono_ns']
        frame['kernel_sof_event_timestamp'] = sof_event['hardware_ns']
        frame['sof_callback'] = sof_event['mono_ns']
        request_key = fdq['request'], fdq['request_sequence']
        for kind, label in [(16, 'ipe_queue'), (17, 'image_processed'), (18, 'internal_return'), (19, 'request_complete')]:
            ev = one(records, lambda e: e['type'] == kind and (e['request'], e['request_sequence']) == request_key,
                     (label, case.name, sof))
            frame[label] = ev['mono_ns']
        assert frame['image_processed'] <= frame['internal_return'] <= frame['request_complete']
        next_queue = [e for e in records if e['type'] == 5 and e['buffer'] == fdq['buffer'] and e['mono_ns'] > frame['internal_return']]
        if next_queue:
            qb = next_queue[0]
            req = one(records, lambda e: e['type'] == 2 and e['request'] == qb['request'] and e['request_sequence'] == qb['request_sequence'],
                      ('next RequestEnter', case.name, sof))
            qr = one(records, lambda e: e['type'] == 6 and e['request'] == qb['request'] and e['request_sequence'] == qb['request_sequence'],
                     ('next QBUF result', case.name, sof))
            assert frame['internal_return'] <= req['mono_ns'] <= qb['mono_ns'] <= qr['mono_ns'] and qr['status'] == 0
            frame.update(next_request_enter=req['mono_ns'], next_qbuf_begin=qb['mono_ns'], next_qbuf_result=qr['mono_ns'])
        context = lsc_context[sof]
        applied = lsc_applied[int(context['revision'])]
        assert context['mesh-trace'] == applied['mesh-trace'] and int(applied['first-sof']) <= sof
        frame_rows.append(frame)
    mathematical = frame_rows[3:]
    assert len(mathematical) == 29 and all('IPE_TONE_PREPARE' in r for r in mathematical)
    assert all('IPE_TONE_BOOTSTRAP' in r for r in frame_rows[:3])
    negative_stop = []
    stop_times = [e['ns'] for e in logs if e['kind'] == 'REQUEST_STOP_CANCEL']
    queued_sofs = {int(v) for v in re.findall(r'IPE_TONE_QUEUE epoch=1 sof=(\d+) ', text)}
    for receipt in raw_receipts:
        if receipt[3] != '0':
            continue
        sof = int(receipt[1])
        assert sof > samples[-1][6] and sof not in queued_sofs
        assert by_sof[sof].get('IPE_TONE_PREPARE')
        assert stop_times and min(stop_times) <= by_sof[sof]['IPE_RECEIPT'][0]['ns']
        negative_stop.append(dict(sof=sof, mathematical_prepare_logged=True,
                                  ipe_queue_logged=False, returned_after_stop_cancel=True,
                                  counted_as_consumed_or_physical_ipe=False))
    assert strict_result['discarded_unqueued_observations'] == len(negative_stop)
    metrics = {}
    for name, start, end in [
        ('pair_to_tone_log', 'IPE_PAIR', 'IPE_TONE_PREPARE'),
        ('tone_log_to_host_return_log', 'IPE_TONE_PREPARE', 'TONE_IPA_PREPARE'),
        ('host_return_to_ipe_queue', 'TONE_IPA_PREPARE', 'ipe_queue'),
        ('ipe_queue_to_image_processed', 'ipe_queue', 'image_processed'),
        ('image_processed_to_receipt_log', 'image_processed', 'IPE_RECEIPT'),
        ('receipt_log_to_internal_return', 'IPE_RECEIPT', 'internal_return'),
        ('internal_return_to_request_complete', 'internal_return', 'request_complete'),
        ('pair_to_receipt_log', 'IPE_PAIR', 'IPE_RECEIPT'),
        ('full_completion_to_pair', 'full_completion_timestamp', 'IPE_PAIR'),
        ('kernel_sof_event_to_callback', 'kernel_sof_event_timestamp', 'sof_callback'),
        ('kernel_sof_event_to_completion', 'kernel_sof_event_timestamp', 'full_completion_timestamp'),
        ('internal_return_to_next_request_enter', 'internal_return', 'next_request_enter'),
        ('next_request_enter_to_qbuf_begin', 'next_request_enter', 'next_qbuf_begin'),
        ('next_qbuf_call', 'next_qbuf_begin', 'next_qbuf_result'),
    ]:
        metrics[name] = metric(timing, [(r[start], r[end]) for r in mathematical if end in r])
    metrics['dispatch_logged'] = timing.summary([r['dispatch_us'] / 1000 for r in mathematical])
    metrics['prior_receipt_to_next_pair'] = metric(timing, [(a['IPE_RECEIPT'], b['IPE_PAIR']) for a, b in zip(mathematical, mathematical[1:])])
    metrics['pair_to_next_pair'] = metric(timing, [(a['IPE_PAIR'], b['IPE_PAIR']) for a, b in zip(mathematical, mathematical[1:])])
    gaps = []
    for left, right in zip(frame_rows, frame_rows[1:]):
        for missing in range(left['sof'] + 1, right['sof']):
            assert missing not in linked
            point = one(records, lambda e: e['type'] == 8 and e['sof'] == missing, ('missing PixSof', case.name, missing))
            timestamp = point['hardware_ns']
            assert timestamp > 0
            recent = [e for e in owner_events if e['ns'] <= timestamp]
            snap = recent[-1] if recent else None
            later_requests = [r for r in records if r['type'] == 2 and r['mono_ns'] >= timestamp]
            later_returns = [r for r in records if r['type'] == 18 and r['mono_ns'] >= timestamp]
            later_qbuf = [r for r in owner_events if r['kind'] == 'vb2_qbuf' and r['ns'] >= timestamp]
            gaps.append(dict(missing_sof=missing, after_sof=left['sof'], before_sof=right['sof'],
                successful_full_dq=False, pd10_observed=bool(by_sof.get(missing, {}).get('PD10_READY')),
                statistics_observed=bool(by_sof.get(missing, {}).get('IPE_OBSERVE')),
                kernel_sof_event_to_callback_ms=timing.delta(timestamp, point['mono_ns']),
                previous_full_completion_to_sof_event_ms=timing.delta(left['full_completion_timestamp'], timestamp),
                sof_event_to_following_full_completion_ms=timing.delta(timestamp, right['full_completion_timestamp']),
                software_snapshot_before_kernel_event=None if snap is None else dict(queued=snap['queued'], owned_by_driver=snap['owned_by_drv'],
                    age_ms=timing.delta(snap['ns'], timestamp)),
                kernel_event_to_next_request_enter_ms=None if not later_requests else timing.delta(timestamp, later_requests[0]['mono_ns']),
                kernel_event_to_next_internal_return_ms=None if not later_returns else timing.delta(timestamp, later_returns[0]['mono_ns']),
                kernel_event_to_next_software_qbuf_ms=None if not later_qbuf else timing.delta(timestamp, later_qbuf[0]['ns']),
                user_snapshot_at_sof_callback=dict(free_full=point['free_full'], outstanding_full=point['outstanding_full'],
                    requests=point['requests'], waiting_full=point['waiting_full'], ipe_active=bool(point['flags'] & 2)),
                physical_fifo_state_or_root_cause_proven=False))
    span = samples[-1][4] - samples[0][4]
    report = dict(name=case.name, proxy_sha256=expected_proxy, actual_proc_exe_verified=True, strict=strict_result,
                  raw_receipts=len(raw_receipts), negative_receipts=sum(r[3] == '0' for r in raw_receipts), receipt_filter_used=False,
                  negative_unqueued_stop_observations=negative_stop,
                  consumed=32, successful_math_samples=29, all_consumed_full_ring_v4l2_vb2_linked=True,
                  full_ring_successful_dq=len(ring_dq), successful_full_not_consumed=len(ring_dq) - 32,
                  lsc_contexts_consistent=32, capacity_active=False, metrics=metrics, gaps=gaps,
                  pipeline_thread_observation=dict(single_actual_tid=True, full_ioctl_cpu_histogram=cpu_histogram,
                      final_same_cpu_dq_run=dict(cpu=last_cpu, first_sof=tail[0]['sequence'],
                                                last_sof=tail[-1]['sequence'], observed_dq_count=len(tail)),
                      cpu_observation_scope='FULL ioctl event points only; not whole-frame residency or IPA worker CPU'),
                  consumed_completion_timestamp_fps=round(31e9 / span, 3),
                  ring={k: v for k, v in ring_summary.items() if not k.startswith('retained_mono_')},
                  inputs_sha256=dict(client_log=sha(log), witness=sha(witness_file), bounded_ring=sha(csv_files[0])))
    return report, frame_rows


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run-root', type=Path)
    parser.add_argument('--health', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    dependencies = modules()
    if args.self_test:
        private = Path('E:/edk2-samurai-out') if Path('E:/').exists() else Path('/mnt/e/edk2-samurai-out')
        retained = private / 'kernel468/runtime-collected-r2/1920x1080-isolated/client.log'
        tested = dependencies[3](retained.read_text(), 's5k3m5', width=1920, height=1080, stride=1920, coarse_bytes=261120)
        assert tested['frames'] == 32 and tested['successful_math'] == 29 and tested['bootstrap'] == 3
        csv_file = private / 'kernel452/runtime-collected-r2/trace-window/captures/full-27901-e1-17268856052455.csv'
        ring, records = dependencies[1].parse_trace(csv_file.read_text())
        assert ring['passed'] and records
        result = dict(stage=471, tool_self_test_passed=True, actual471_hardware_examined=False,
                      reused_strict_auditor_sha256=dependencies[4], retained468_strict_frames=32,
                      retained452_ring_records=len(records), pending_actual471=True)
        (HERE / 'analysis-tool-validation.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        return
    assert args.run_root and args.health
    run = args.run_root
    state = json.loads((run / 'state.json').read_bytes())
    plan = json.loads((run / 'comparison-plan-private.json').read_bytes())
    assert state['terminal'] and state['passed'] and not state['failure'] and not state.get('cleanup_failure')
    assert state['formal_modules_restored'] and state['services_restored'] and state['sensor_module_restored']
    assert state['tele_final_checks']['passed']
    assert state['taint_before'] == state['taint_after'] == 0 and not state['new_faults']
    handoff = json.loads((run / 'handoff-private.json').read_bytes())
    assert state['tele_charging_before'] == state['tele_charging_after'] == handoff['charging']
    assert plan['common_payload']['lib/libcamera.so.0.7.2'] == CORE
    assert plan['common_payload']['factory-s5k3m5-private.yaml'] == PROFILE
    assert IPA in plan['common_payload'].values() and plan['common_payload']['gst-sustained'] == CLIENT
    assert [s['name'] for s in plan['segments']] == CASES
    assert [s['proxy_sha256'] for s in plan['segments']] == [OLD, NEW, OLD]
    assert plan['sensor_mode'] == 2 and plan['actual_sensor'] == [4208, 2368]
    proof = json.loads((run / 'proof.json').read_bytes())
    assert proof['sensor']['sha256'] == SENSOR and state['candidate_sensor_note'] == proof['sensor']['note_sha256']
    guard = dependencies[2]
    trace_plan = guard.GuardedPlan((run / 'probe-private.json').read_bytes(), (run / 'selection-private.json').read_bytes(),
                                   (run / 'extra-private.json').read_bytes(), (run / 'graph-private.txt').read_bytes())
    assert trace_plan.full_role == state['full_role']
    evidence = run / trace_plan.name
    trace_state = json.loads((evidence / 'state.json').read_bytes())
    assert trace_state['phase'] == 'cleaned' and trace_state['unrelated_selected_controls_unchanged'] and not trace_state['errors']
    attempt = trace_state['capture_attempts'][-1]
    assert attempt['complete'] and attempt['online_cpus_unchanged']
    trace = evidence / 'trace-private-1.txt'
    assert sha(trace) == attempt['trace']['sha256']
    trace_events = dependencies[0].parse_trace(trace)
    emission = guard.role.check_emission(trace_plan.full_role, [dict(e, event=e['kind']) for e in trace_events])
    assert emission == state['full_emission']
    cpu_stats = []
    for file in sorted(evidence.glob('stats-private-1-cpu*.txt')):
        values = dict(re.findall(r'^([^:\n]+):\s*(.+)$', file.read_text(), re.M))
        row = {key: int(values[key]) for key in ['overrun', 'commit overrun', 'dropped events']}
        assert not any(row.values())
        cpu_stats.append(row)
    assert len(cpu_stats) == 8
    reports, rows = [], []
    for name, proxy in zip(CASES, [OLD, NEW, OLD]):
        report, frame_rows = inspect_case(run / name, proxy, trace_events, trace_plan.full_role,
                                           state['sustained'][name], dependencies)
        reports.append(report)
        rows.append(dict(case=name, frames=frame_rows))
    physical = sum(s['ipe_completed'] for s in state['sustained'].values())
    final = state['candidate_final_status']
    assert final['jobs'] == final['completed'] == final['direct_completed'] == physical
    assert not any(final[k] for k in ['failed', 'cancelled', 'first_error', 'fatal', 'pinned', 'orphans', 'users', 'running'])
    health = json.loads(args.health.read_bytes())
    assert health['health_audit']['passed']
    assert health['health_audit']['manifest_sha256'] == handoff['charging']['manifest_sha256']
    for key in ['external_worker_exit_verified', 'formal_notes_verified', 'trace_instance_absent',
                'actual_restored_uid10000_services_verified', 'user_directory_absent']:
        assert health[key]
    kernel_log = (run / 'kernel-log-private.txt').read_text()
    assert kernel_log.strip() and all(line in health['dmesg'] for line in kernel_log.splitlines())
    comparisons = {}
    for key in reports[0]['metrics']:
        values = [r['metrics'][key]['median_ms'] for r in reports]
        comparisons[key] = dict(A1_old=values[0], B_new=values[1], A2_old=values[2],
                               B_minus_A1_ms=round(values[1] - values[0], 3), B_minus_A2_ms=round(values[1] - values[2], 3))
    private = args.health.parent
    capacity_path = private.parent / 'kernel448/charging-baseline-private.json'
    capacities = json.loads(capacity_path.read_bytes())['cpu_capacity']
    assert set(capacities) == {str(i) for i in range(8)}
    for report in reports:
        observation = report['pipeline_thread_observation']
        observation['historical_capacity_group_ioctl_counts'] = {
            kind: dict(sorted(collections.Counter({capacity: sum(count for cpu, count in cpus.items()
                                                              if str(capacities[cpu]) == capacity)
                                                  for capacity in {str(capacities[cpu]) for cpu in cpus}}).items()))
            for kind, cpus in observation['full_ioctl_cpu_histogram'].items()}
    (private / 'comparison-frame-times-private.json').write_text(json.dumps(rows, indent=2) + '\n')
    result = dict(stage=471, passed=True, consumed=96, physical_ipe_completed=physical,
                  successful_math_samples=87, bootstrap_consumed=9, cases=reports,
                  raw_receipts=sum(r['raw_receipts'] for r in reports),
                  negative_unqueued_stop_receipts=sum(r['negative_receipts'] for r in reports),
                  successful_full_dq=sum(r['full_ring_successful_dq'] for r in reports),
                  successful_full_not_consumed=sum(r['successful_full_not_consumed'] for r in reports),
                  full_ioctl_emission=emission,
                  median_comparisons_ms=comparisons, reused_strict_auditor_sha256=dependencies[4],
                  raw_receipts_filtered=False, full_trace_roles_and_live_fds_verified=True,
                  bounded_rings_all_three_segments=True, guarded_trace_overrun_commit_drop_all_zero=True,
                  formal_restore_and_external_health_verified=True,
                  physical_fifo_or_gap_root_cause_proven=False, long_term_zero_gap_proven=False,
                  production_proxy_permanently_changed=False,
                  timing_scope='all29 consumed mathematical frames per segment; wall clock includes scheduling/IPC/logging',
                  kernel_sof_time_is_irq_event_timestamp_not_physical_edge=True,
                  cpu_capacity_group_reference=dict(source='kernel448/charging-baseline-private.json',
                       sha256=sha(capacity_path), capacities=capacities, historical_only=True,
                       fresh471_capacity_frequency_or_worker_cpu_sample_available=False),
                  inputs_sha256=dict(state=sha(run / 'state.json'), plan=sha(run / 'comparison-plan-private.json'),
                                     full_trace=sha(trace), health=sha(args.health)))
    (HERE / 'analysis-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(stage=471, passed=True, consumed=96, gap_counts=[len(r['gaps']) for r in reports])))


if __name__ == '__main__':
    main()
