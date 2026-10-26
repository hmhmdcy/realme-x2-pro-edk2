"""Correlate retained 467/468 traces and logs; never access the phone or SDK.

FULL timestamps in this candidate are IRQ completion timestamps.  The SOF
messages are userspace delivery logs.  Neither is a physical SOF edge record.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import statistics

HERE = Path(__file__).resolve().parent
OLD_PROXY = 'c7887708377b92b167d917173cb2840a78e437a773985fa087ef980bd382038c'
PIPELINE = 'befec1da3743545652adc669cc649860d6840738e38a3798305d213b2e874b40'
KERNEL = '42a8d6ff74228bb8847adc60b4354e19ba803c88a0b2ceef8c163748c7835bdc'
CLIENT = '7f4d6a1f8527280d8bbe11e6af638348200bd9bc8465be8357cdc0ca732b852a'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def delta(a, b):
    return round((b - a) / 1e6, 3)


def summary(values):
    values = sorted(values)
    assert values
    return dict(n=len(values), minimum_ms=round(values[0], 3),
                median_ms=round(statistics.median(values), 3),
                p95_ms=round(values[(len(values) - 1) * 95 // 100], 3),
                maximum_ms=round(values[-1], 3))


def parse_trace(path):
    events = []
    for line in path.read_text().splitlines():
        match = re.match(r'^\s*(.*)-(\d+)\s+\[(\d+)\]\s+\S+\s+'
                         r'(\d+)\.(\d+):\s+(\w+): (.*)$', line)
        if not match:
            continue
        _, pid, cpu, sec, frac, kind, payload = match.groups()
        event = dict(kind=kind, pid=int(pid), cpu=int(cpu),
                     ns=int(sec) * 10**9 + int(frac.ljust(9, '0')))
        for key, value in re.findall(
                r'(owner|queued|owned_by_drv|index|type|bytesused|timestamp|sequence|minor) = ([^,]+)', payload):
            event[key] = int(value) if value.isdecimal() else value
        events.append(event)
    return sorted(events, key=lambda event: event['ns'])


def parse_log(text):
    events, frames = [], {}
    for line in text.splitlines():
        match = re.match(r'^\[(\d+):(\d+):(\d+)\.(\d{9})\] \[(\d+)\]'
                         r'\s+\S+\s+\S+\s+\S+:\d+\s+([A-Z][A-Z0-9_]+) (.*)$', line)
        if not match:
            continue
        hour, minute, sec, frac, pid, kind, payload = match.groups()
        event = dict(kind=kind, pid=int(pid),
                     ns=((int(hour) * 60 + int(minute)) * 60 + int(sec)) * 10**9 + int(frac))
        event.update(re.findall(r'([\w-]+)=([^ ]+)', payload))
        if 'sof' in event:
            event['sof'] = int(event['sof'])
        elif kind == 'SOF':
            event['sof'] = int(event['sequence'])
        events.append(event)
        if 'sof' in event:
            frames.setdefault(event['sof'], {}).setdefault(kind, []).append(event)
    return events, frames


def analyze(root, stage, attempt):
    original = root / f'kernel{stage}' / f'runtime-collected-{attempt}'
    selection = json.loads((original / 'selection-private.json').read_bytes())
    trace = original / selection['instance'] / 'trace-private-1.txt'
    events = parse_trace(trace)
    results, private_rows = [], []
    for case in ['1280x720-isolated', '1920x1080-isolated']:
        log = original / case / 'client.log'
        text = log.read_text()
        assert re.search(r'FOCUS_WORKSPACE_PREPARE epoch=1 .* bytes=0$', text, re.M)
        assert re.search(r'CAPACITY_STOP epoch=1 .* reason=inactive active=0 users=0 ', text)
        assert 'FOCUS_TIMING ' not in text and 'CAPACITY_START ' not in text
        logs, by_sof = parse_log(text)
        low, high = min(e['ns'] for e in logs), max(e['ns'] for e in logs)
        witness_path = original / case / 'live-witness-private.json'
        witness = json.loads(witness_path.read_bytes())
        assert witness['isolated'] and witness['application']['exe_sha256'] == CLIENT
        plan = json.loads((original / 'tele-plan-private.json').read_bytes())
        assert OLD_PROXY in plan['common_payload'].values()
        dq = [e for e in events if e['kind'] == 'v4l2_dqbuf'
              and e.get('minor') == selection['full_minor'] and low <= e['ns'] <= high]
        paired = {}
        for event in dq:
            found = [e for e in events if e['kind'] == 'vb2_dqbuf'
                     and e['pid'] == event['pid'] and e['index'] == event['index']
                     and e['timestamp'] // 1000 * 1000 == event['timestamp']
                     and 0 <= event['ns'] - e['ns'] < 2_000_000]
            assert len(found) == 1 and event['sequence'] not in paired
            paired[event['sequence']] = event, found[0]
        images = [tuple(map(int, m)) for m in re.findall(
            r'^GST_IMAGE frame=(\d+) .* sequence=(\d+) wall-ns=(\d+)$', text, re.M)]
        assert len(images) == 32
        rows = []
        for number, sof, gst_time in images:
            dq_event, vb2 = paired[sof]
            row = dict(frame=number, sof=sof, index=dq_event['index'], gst=gst_time,
                       full_dq=dq_event['ns'], full_completion_timestamp=vb2['timestamp'])
            for name in ['SOF', 'PD10_READY', 'IPE_OBSERVE', 'IPE_PAIR',
                         'IPE_TONE_BOOTSTRAP', 'IPE_TONE_PREPARE',
                         'TONE_IPA_PREPARE', 'IPE_TONE_QUEUE', 'IPE_RECEIPT']:
                found = by_sof[sof].get(name, [])
                if found:
                    assert len(found) == 1, (stage, case, sof, name)
                    row[name] = found[0]['ns']
            receipt = by_sof[sof]['IPE_RECEIPT'][0]
            assert receipt['success'] == receipt['result'] == '1'
            row['dispatch_us'] = int(by_sof[sof]['TONE_IPA_PREPARE'][0]['dispatch-us'])
            done = [e for e in events if e['kind'] == 'vb2_buf_done'
                    and e.get('owner') == vb2['owner'] and e['timestamp'] == vb2['timestamp']]
            assert len(done) == 1
            row['full_done'] = done[0]['ns']
            q = [e for e in events if e['kind'] == 'v4l2_qbuf'
                 and e.get('minor') == selection['full_minor'] and e['pid'] == dq_event['pid']
                 and e['index'] == dq_event['index'] and dq_event['ns'] < e['ns'] <= high]
            row['next_same_index_qbuf'] = q[0]['ns'] if q else None
            rows.append(row)
        math = rows[3:]
        assert len(math) == 29 and all('IPE_TONE_PREPARE' in row for row in math)
        assert all('IPE_TONE_BOOTSTRAP' in row for row in rows[:3])
        metrics = {}
        for name, start, end in [
            ('pair_to_tone_log', 'IPE_PAIR', 'IPE_TONE_PREPARE'),
            ('tone_log_to_host_return_log', 'IPE_TONE_PREPARE', 'TONE_IPA_PREPARE'),
            ('host_return_to_ipe_queue_log', 'TONE_IPA_PREPARE', 'IPE_TONE_QUEUE'),
            ('ipe_queue_to_receipt_log', 'IPE_TONE_QUEUE', 'IPE_RECEIPT'),
            ('pair_to_receipt_log', 'IPE_PAIR', 'IPE_RECEIPT'),
            ('full_completion_to_pair', 'full_completion_timestamp', 'IPE_PAIR'),
            ('full_completion_to_dq', 'full_completion_timestamp', 'full_dq'),
            ('receipt_to_gst_log', 'IPE_RECEIPT', 'gst'),
        ]:
            metrics[name] = summary([delta(row[start], row[end]) for row in math])
        metrics['dispatch_logged'] = summary([row['dispatch_us'] / 1000 for row in math])
        consecutive = list(zip(rows[3:-1], rows[4:]))
        metrics['prior_receipt_to_next_pair'] = summary([
            delta(before['IPE_RECEIPT'], after['IPE_PAIR']) for before, after in consecutive])
        metrics['pair_to_next_pair'] = summary([
            delta(before['IPE_PAIR'], after['IPE_PAIR']) for before, after in consecutive])
        requeued = [(before, after) for before, after in consecutive
                    if before['next_same_index_qbuf'] is not None]
        for name, field, use_next in [
            ('same_index_qbuf_after_own_receipt', 'IPE_RECEIPT', False),
            ('same_index_qbuf_after_own_gst', 'gst', False),
            ('same_index_qbuf_after_next_receipt', 'IPE_RECEIPT', True),
            ('same_index_qbuf_after_next_gst', 'gst', True),
        ]:
            metrics[name] = summary([delta((after if use_next else before)[field],
                                          before['next_same_index_qbuf'])
                                     for before, after in requeued])
        owner = paired[rows[0]['sof']][1]['owner']
        owner_events = [e for e in events if e.get('owner') == owner and low <= e['ns'] <= high]
        gaps = []
        for left, right in zip(rows, rows[1:]):
            if right['sof'] == left['sof'] + 1:
                continue
            missing = list(range(left['sof'] + 1, right['sof']))
            assert len(missing) == 1
            sof = missing[0]
            assert sof not in paired
            marker = by_sof[sof]['SOF'][0]['ns']
            snapshot = [e for e in owner_events if e['ns'] <= marker][-1]
            window = [e for e in owner_events if left['full_dq'] < e['ns'] <= right['full_dq']]
            done = [e for e in window if e['kind'] == 'vb2_buf_done']
            assert len(done) == 1 and done[0]['timestamp'] == right['full_completion_timestamp']
            gaps.append(dict(
                missing_sof=sof, previous_sof=left['sof'], following_sof=right['sof'],
                completion_timestamp_interval_ms=delta(left['full_completion_timestamp'], right['full_completion_timestamp']),
                neighbouring_dq_interval_ms=delta(left['full_dq'], right['full_dq']),
                previous_completion_to_missing_sof_delivery_log_ms=delta(left['full_completion_timestamp'], marker),
                missing_sof_delivery_log_to_following_completion_ms=delta(marker, right['full_completion_timestamp']),
                pd10_delivery_after_missing_sof_log_ms=delta(marker, by_sof[sof]['PD10_READY'][0]['ns']),
                statistics_observed_after_missing_sof_log_ms=delta(marker, by_sof[sof]['IPE_OBSERVE'][0]['ns']),
                last_software_snapshot_at_sof_log=dict(queued=snapshot['queued'], owned_by_driver=snapshot['owned_by_drv'],
                                                     age_ms=delta(snapshot['ns'], marker)),
                physical_sof_edge_or_fifo_state_recorded=False,
                missing_full_dq=True, following_only_full_done_in_dq_interval=True))
        expected = [] if case.startswith('1280') else ([14, 21, 28] if stage == 467 else [17, 23, 31])
        assert [g['missing_sof'] for g in gaps] == expected
        results.append(dict(stage=stage, capture=case, consumed=32, successful_math_sample=29,
                            capacity_active=False, metrics=metrics, gaps=gaps,
                            inputs_sha256=dict(client_log=sha(log), full_trace=sha(trace), witness=sha(witness_path))))
        private_rows.append(dict(stage=stage, case=case, rows=rows))
    return results, private_rows


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--private-root', type=Path, default=Path('E:/edk2-samurai-out') if Path('E:/').exists() else Path('/mnt/e/edk2-samurai-out'))
    args = parser.parse_args()
    assert sha(args.private_root / 'kernel461/camss_vfe-candidate.cpp') == PIPELINE
    source = json.loads((args.private_root / 'kernel470/source-inspect-private.json').read_bytes())
    assert source['source354/drivers/media/platform/qcom/camss/camss-vfe.c']['sha256'] == KERNEL
    extract = source['source354/drivers/media/platform/qcom/camss/camss-vfe.c']['extract']
    assert '@ts: completion timestamp' in extract and 'ready_buf->vb.vb2_buf.timestamp = ts;' in extract
    results, private_rows = [], []
    for stage, attempt in [(467, 'r1'), (468, 'r2')]:
        a, b = analyze(args.private_root, stage, attempt)
        results.extend(a)
        private_rows.extend(b)
    (args.private_root / 'kernel470/timing-rows-private.json').write_text(json.dumps(private_rows, indent=2) + '\n')
    report = dict(stage=470, passed=True, cached_only=True, phone_accessed=False,
                  source_hashes=dict(pipeline461=PIPELINE, camss441=KERNEL),
                  units='milliseconds; logs are wall-clock boundaries, not CPU accounting',
                  sample='all 29 successful mathematical frames after each three bootstrap frames',
                  full_timestamp_semantics='IRQ completion timestamp; not physical SOF',
                  sof_message_semantics='userspace delivery log; underlying event timestamp not printed',
                  worker_cpu_and_encode_decode_timings_available=False,
                  application_unref_pool_release_queue_call_timestamps_available=False,
                  production_tuning_capacity_buffer_or_driver_changed=False, rows=results,
                  next_minimum_candidate='reuse451 wire-compatible single-allocation proxy only; retain461 core/444 IPA6/history and468 mode2',
                  physical_drop_root_cause_or_fix_proven=False)
    (HERE / 'timing-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(stage=470, passed=True, cases=len(results), gaps=sum(len(r['gaps']) for r in results))))


if __name__ == '__main__':
    main()
