"""Pure cached-log checks for the finite installed-stack482 probes."""
import re


def rows(text, name):
    return [dict(re.findall(r'([a-z][a-z0-9-]*)=([^\s]+)', line))
            for line in text.splitlines() if name + ' ' in line]


def one(text, name):
    found = rows(text, name)
    assert len(found) == 1, (name, len(found))
    return found[0]


def audit_history(text):
    observations = rows(text, 'IPE_OBSERVE')
    by_token = {int(r['token']): r for r in observations}
    assert len(by_token) == len(observations)
    queues = rows(text, 'IPE_TONE_QUEUE')
    queue = {int(r['token']): r for r in queues}
    assert len(queue) == len(queues)
    receipts = rows(text, 'IPE_RECEIPT')
    receipt = {int(r['token']): r for r in receipts}
    assert len(receipt) == len(receipts)
    for token, row in receipt.items():
        assert token in by_token
        observation = by_token[token]
        assert all(row[key] == observation[key] for key in ['epoch', 'sof', 'trace'])
        assert (row['success'], row['result']) in [('1', '1'), ('0', '0')]
        if token not in queue:
            assert row['success'] == row['result'] == '0'
    history = {k: int(v) for k, v in one(text, 'IPE_HISTORY_STOP').items() if k != 'epoch'}
    assert history['pending'] == history['superseded'] == 0
    assert history['prepared'] == len(observations) == history['committed'] + history['discarded'] + history['aborted']
    assert history['committed'] == sum(r['success'] == '1' for r in receipt.values())
    assert history['discarded'] == sum(r['success'] == '0' for r in receipt.values())
    assert history['aborted'] == len(set(by_token) - set(receipt))
    numeric, numeric_receipts = {}, {}
    revision, pending = 0, None
    for line in text.splitlines():
        if 'IPE_TONE_PREPARE ' in line:
            row = one(line, 'IPE_TONE_PREPARE')
            token = int(row['token'])
            assert pending is None and token not in numeric and token in by_token
            observation = by_token[token]
            assert row['epoch'] == observation['epoch'] and row['sof'] == observation['sof']
            assert row['histogram'] == observation['trace']
            assert int(row['base']) == revision and int(row['revision']) == revision + 1
            numeric[token] = row
            pending = token
        if 'IPE_TONE_RECEIPT ' in line:
            row = one(line, 'IPE_TONE_RECEIPT')
            token = int(row['token'])
            assert token == pending and token not in numeric_receipts
            prepared = numeric[token]
            assert all(row[key] == prepared[key] for key in ['epoch', 'sof', 'gtm-cookie', 'gtm-generation'])
            assert (row['success'], row['result']) in [('1', '1'), ('0', '0')]
            if row['success'] == '1':
                assert token in queue and token in receipt and receipt[token]['success'] == '1'
                revision += 1
            else:
                assert token not in receipt or receipt[token]['success'] == '0'
            assert int(row['revision']) == revision
            numeric_receipts[token] = row
            pending = None
    tone_stop = one(text, 'IPE_TONE_STOP')
    assert int(tone_stop['revision']) == revision and int(tone_stop['pending']) == int(pending is not None)
    if pending is not None:
        assert pending not in receipt or receipt[pending]['success'] == '0'
    assert set(numeric) == set(numeric_receipts) | ({pending} if pending is not None else set())
    bootstraps = {int(r['sof']): r for r in rows(text, 'IPE_TONE_BOOTSTRAP')}
    holds = {int(r['token']): r for r in rows(text, 'IPE_TONE_HOLD')}
    for token, row in queue.items():
        if row['fresh'] == '1':
            assert token in numeric and row['revision'] == numeric[token]['revision']
        else:
            assert row['fresh'] == '0'
            if int(row['sof']) not in bootstraps:
                assert token in holds and all(row[key] == holds[token][key] for key in ['epoch', 'sof', 'revision', 'bytes'])
    return by_token, queue, receipt, history, numeric, numeric_receipts, revision


def audit(text, *, model, kind, before, after):
    assert one(text, 'FIXTURE_RESTORATION')['result'] == '0'
    assert one(text, 'FIXTURE_RESULT')['result'] == '0'
    child = one(text, 'FIXTURE_CHILD')
    assert child['exited'] == '1' and child['exit'] == '0' and child['signalled'] == '0'
    assert not any(token in text for token in ['IPE_TONE_REJECT', 'IFE_GTM_REJECT',
        'IMAGE_PAIR_TIMEOUT', 'Missing SOF tag', 'Stream stop failed:', 'IPA rejected statistics'])
    if kind == 'gst':
        result = one(text, 'GST_RESULT')
        assert result == dict(frames='32', width='640', height='480', **{'bus-errors': '0'}, result='0')
        images = rows(text, 'GST_IMAGE')
        assert len(images) == 32 and [int(r['frame']) for r in images] == list(range(32))
        assert all((r['width'], r['height'], r['bytes']) == ('640', '480', '460800') for r in images)
        assert all(int(r['hash']) > 0 for r in images)
        assert all(int(b['pts']) > int(a['pts']) and int(b['sequence']) > int(a['sequence'])
                   for a, b in zip(images, images[1:]))
        identity = one(text, 'APPLICATION_IDENTITY')
        assert identity['uid'] == identity['euid'] == '10000' and int(identity['capeff'], 16) == 0
        frames = 32
        delivered = {int(r['sequence']) for r in images}
    else:
        result = one(text, 'RAW_RESULT')
        assert result['model'] == model and result['kind'] == kind
        assert result['failed'] == result['result'] == '0' and int(result['frames']) >= 6
        frames = int(result['frames'])
        images = rows(text, 'RAW_IMAGE')
        assert len(images) == frames * (2 if kind == 'dual' else 1)
        assert all(r['status'] == '0' and int(r['bytes']) > 0 and int(r['sample-hash']) > 0 for r in images)
        pairs = rows(text, 'RawPair')
        assert len(pairs) == frames and all(r['matched'] == '1' for r in pairs)
        configurations = re.findall(r'^RAW_CONFIG (.+)$', text, re.M)
        native_size = '4608x3456' if model == 's5kgw1' else '2104x1560'
        assert sum(bool(re.fullmatch(native_size + r'-S[A-Z]+10_CSI2P/RAW', row)) for row in configurations) == 1
        assert configurations.count('640x480-NV12/sYCC') == (1 if kind == 'dual' else 0)
        assert len(configurations) == (2 if kind == 'dual' else 1)
        delivered = {int(r['sequence']) for r in images if r['format'] == 'NV12'}
    by_token, queue, receipt, history, numeric, numeric_receipts, revision = audit_history(text)
    queues = list(queue.values())
    delta = {key: after[key] - before[key] for key in ['jobs', 'completed', 'cancelled', 'direct_completed']}
    assert all(value >= 0 for value in delta.values())
    assert delta['jobs'] == delta['completed'] + delta['cancelled'] and delta['direct_completed'] == delta['completed']
    starts, stops = rows(text, 'CAPACITY_START'), rows(text, 'CAPACITY_STOP')
    assert len(stops) == 1 and stops[0]['status'] == stops[0]['active'] == stops[0]['users'] == '0'
    assert len(starts) <= 1 and all(r['status'] == '0' for r in starts)
    if starts and starts[0]['active'] == '1':
        assert stops[0]['tid'] == starts[0]['tid'] and stops[0]['original'] == starts[0]['original']
        assert stops[0]['reason'] in ['restored', 'restored-constrained'], stops[0]
    if kind == 'raw':
        assert not queues and not delta['jobs'] and not delta['completed'] and not delta['cancelled']
        assert history['committed'] == 0 and history['discarded'] + history['aborted'] == history['prepared']
        assert not any(x in text for x in ['IPE enabled ', 'PD10_READY ', 'IPE_TONE_PREPARE ', 'IPE_TONE_QUEUE '])
        successes, queued_failures = {}, {}
    else:
        assert len(starts) == 1
        assert 'IPE enabled 640x480-NV12/sYCC requests=1 pd10=1' in text
        assert queues and all(r['result'] == '0' and r['pd10'] == '1' for r in queues)
        assert all(t in by_token and r['sof'] == by_token[t]['sof'] for t, r in queue.items())
        assert all(int(b['sof']) > int(a['sof']) for a, b in zip(queues, queues[1:]))
        pd10 = {int(r['sof']) for r in rows(text, 'PD10_READY')}
        assert all(int(r['sof']) in pd10 for r in queues)
        successes = {t: r for t, r in receipt.items() if r['success'] == r['result'] == '1'}
        queued_failures = {t: receipt[t] for t in set(queue) & set(receipt) if t not in successes}
        assert all(r['success'] == r['result'] == '0' for r in queued_failures.values())
        assert all(r['sof'] == queue[t]['sof'] for t, r in receipt.items() if t in queue)
        assert history['committed'] == len(successes)
        assert set(successes) <= set(queue) and len(queue) == delta['jobs']
        assert delta['completed'] + delta['cancelled'] == len(queue)
        assert {int(queue[t]['sof']) for t in successes} >= delivered
        # A completed-but-undelivered Gst buffer and stop-time queued work are
        # retained; numerical/bootstrap counts are read, never fixed to3/29.
    warnings = [line for line in text.splitlines() if re.search(r'\b(?:WARN|ERROR)\b', line)]
    return dict(passed=True, model=model, kind=kind, frames=frames, delivered_sofs=sorted(delivered),
                ipe_delta=delta, history=history, queues=len(queue), successful_receipts=len(successes),
                stop_classes=dict(queued_failed_receipts=len(queued_failures),
                    queued_unacknowledged_aborted=len(set(queue) - set(receipt)),
                    unqueued_failed_receipts=len(set(receipt) - set(queue)),
                    unqueued_unacknowledged_aborted=len(set(by_token) - set(queue) - set(receipt))),
                bootstrap=len(rows(text, 'IPE_TONE_BOOTSTRAP')),
                numerical_prepares=len(numeric), numerical_commits=revision,
                numerical_stop_aborted_tokens=sorted(set(numeric) - set(numeric_receipts)),
                numerical_receipts=list(numeric_receipts.values()), capacity_start=starts,
                capacity_stop=stops, warnings_and_errors=warnings,
                extra_successful_processed_sofs=sorted({int(queue[t]['sof']) for t in successes} - delivered))
