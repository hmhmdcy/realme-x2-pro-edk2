"""Pure491 GST protocol audit, derived from frozen482 and440/441/443.

No target access. Original observations, failed receipts and stop aborts remain
distinct. A sampled image hash proves buffer sampling, not full image equality.
"""
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
    epoch = one(text, 'IPE_HISTORY_STOP')['epoch']
    assert all(row['epoch'] == epoch for row in observations + queues + receipts)
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
    assert tone_stop['epoch'] == epoch
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


def audit(text, *, model, width, height, frames, before, after, require_fixed_warnings=True):
    assert one(text, 'FIXTURE_RESTORATION')['result'] == '0'
    assert one(text, 'FIXTURE_RESULT')['result'] == '0'
    child = one(text, 'FIXTURE_CHILD')
    assert child['exited'] == '1' and child['exit'] == '0' and child['signalled'] == '0'
    assert not any(token in text for token in ['IPE_TONE_REJECT', 'IFE_GTM_REJECT',
        'IMAGE_PAIR_TIMEOUT', 'Missing SOF tag', 'Stream stop failed:', 'IPA rejected statistics'])
    result = one(text, 'GST_RESULT')
    assert result == dict(frames=str(frames), width=str(width), height=str(height), **{'bus-errors': '0'}, result='0')
    images = rows(text, 'GST_IMAGE')
    assert len(images) == frames and [int(r['frame']) for r in images] == list(range(frames))
    assert all((r['width'], r['height'], r['bytes']) == (str(width), str(height), str(width*height*3//2)) for r in images)
    assert all(int(r['hash']) > 0 for r in images)
    assert all(int(b['pts']) > int(a['pts']) and int(b['sequence']) > int(a['sequence'])
               for a, b in zip(images, images[1:]))
    identity = one(text, 'APPLICATION_IDENTITY')
    assert identity['uid'] == identity['euid'] == '10000' and int(identity['capeff'], 16) == 0
    delivered = {int(r['sequence']) for r in images}
    by_token, queue, receipt, history, numeric, numeric_receipts, revision = audit_history(text)
    queues = list(queue.values())
    delta = {key: after[key] - before[key] for key in ['jobs', 'completed', 'cancelled', 'direct_completed']}
    assert all(value >= 0 for value in delta.values())
    assert delta['jobs'] == delta['completed'] + delta['cancelled'] and delta['direct_completed'] == delta['completed']
    starts, stops = rows(text, 'CAPACITY_START'), rows(text, 'CAPACITY_STOP')
    assert all(row['epoch'] == one(text, 'IPE_HISTORY_STOP')['epoch'] for row in starts + stops)
    assert len(stops) == 1 and stops[0]['status'] == stops[0]['active'] == stops[0]['users'] == '0'
    assert len(starts) <= 1 and all(r['status'] == '0' for r in starts)
    if starts and starts[0]['active'] == '1':
        assert stops[0]['tid'] == starts[0]['tid'] and stops[0]['original'] == starts[0]['original']
        assert stops[0]['reason'] in ['restored', 'restored-constrained'], stops[0]
    assert len(starts) == 1
    assert starts[0]['active'] == starts[0]['users'] == '1'
    assert stops[0]['reason'] == 'restored' and stops[0]['selected'] == starts[0]['selected']
    assert f'IPE enabled {width}x{height}-NV12/sYCC requests=1 pd10=1' in text
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
    assert len(successes) <= delta['completed']
    assert delta['completed'] + delta['cancelled'] == len(queue)
    assert {int(queue[t]['sof']) for t in successes} >= delivered
    # A completed-but-undelivered Gst buffer and stop-time queued work are
    # retained; numerical/bootstrap counts are read, never fixed to3/29.
    protocol = audit_domains(text, model, width, height, by_token, queue, receipt, numeric, numeric_receipts, delivered)
    warnings = warning_summary(text)
    if require_fixed_warnings:
        assert not any(warnings['target_counts'].values()), warnings['target_lines']
    return dict(passed=True, model=model, kind='gst', width=width, height=height, frames=frames, delivered_sofs=sorted(delivered),
                ipe_delta=delta, history=history, queues=len(queue), successful_receipts=len(successes),
                stop_classes=dict(queued_failed_receipts=len(queued_failures),
                    queued_unacknowledged_aborted=len(set(queue) - set(receipt)),
                    unqueued_failed_receipts=len(set(receipt) - set(queue)),
                    unqueued_unacknowledged_aborted=len(set(by_token) - set(queue) - set(receipt))),
                bootstrap=len(rows(text, 'IPE_TONE_BOOTSTRAP')),
                numerical_prepares=len(numeric), numerical_commits=revision,
                numerical_stop_aborted_tokens=sorted(set(numeric) - set(numeric_receipts)),
                numerical_receipts=list(numeric_receipts.values()), capacity_start=starts,
                raw_receipts=list(receipt.values()), unresolved_observation_tokens=sorted(set(by_token)-set(receipt)),
                delivered_sof_gaps=[dict(after=a, before=b, missing=list(range(a+1, b))) for a, b in zip(sorted(delivered), sorted(delivered)[1:]) if b > a+1],
                capacity_stop=stops, warnings=warnings, warnings_and_errors=warnings['warnings_and_errors'], protocol=protocol,
                extra_successful_processed_sofs=sorted({int(queue[t]['sof']) for t in successes} - delivered))


def warning_summary(text):
    lines = text.splitlines()
    selectors = {
        'static_properties': lambda s: 'No static properties available for ' in s or 'Please consider updating the camera sensor properties database' in s,
        'media_bus_0x2027': lambda s: '0x2027' in s and ('Unsupported media bus format' in s or 'Unknown subdev format' in s),
        'build_tree_ipa': lambda s: 'libcamera is not installed. Adding ' in s and 'IPA search path' in s,
        'root_home_configuration': lambda s: 'Failed to open configuration file ' in s and '/root/.config/libcamera/configuration.yaml' in s,
    }
    target = {key: [line for line in lines if select(line)] for key, select in selectors.items()}
    return dict(target_counts={key: len(value) for key, value in target.items()}, target_lines=target,
                warnings_and_errors=[line for line in lines if re.search(r'\b(?:WARN|ERROR)\b', line)])


def audit_domains(text, model, width, height, observations, queues, receipts, numeric, numeric_receipts, delivered):
    """440/443 same-SOF WB/GTM contract without their fixed bootstrap/lock counts.

    Front factory profile keeps IFE GTM off and uses IPE CCM; preserve those
    choices. Successful math must actually reach at least one delivered SOF.
    """
    by_sof = {int(row['sof']): row for row in observations.values()}
    assert len(by_sof) == len(observations)
    gtm, applied, awb, wb, boot, holds, ccm, pd10 = {}, {}, {}, {}, {}, {}, {}, {}
    previous_lux = 0.0
    last_awb = None
    held = 0
    # These are the three finite known PD10 geometries (same source layout).
    coarse_bytes = {(640, 480): 46080, (1280, 720): 123648, (1920, 1080): 261120}[width, height]
    for line in text.splitlines():
        row = dict(re.findall(r'([a-z][a-z0-9-]*)=([^\s]+)', line))
        if 'IFE_GTM_QUEUE ' in line:
            cookie = int(row['cookie']); assert cookie not in gtm
            assert row['enabled'] == ('1' if model != 'imx471' and row['ready'] == '1' else '0')
            gtm[cookie] = row
        if 'IFE_GTM_APPLIED ' in line:
            cookie = int(row['cookie']); assert cookie in gtm and cookie not in applied
            assert all(row[key] == gtm[cookie][key] for key in ['epoch', 'revision', 'source-sof', 'source-histogram', 'ready'])
            assert int(row['generation']) == len(applied) + 1
            applied[cookie] = row
        if 'PD10_READY ' in line:
            sof = int(row['sof']); assert sof not in pd10 and int(row['bytes']) == coarse_bytes
            pd10[sof] = row
        if 'AWB_STATE ' in line:
            sof = int(row['sof']); assert sof not in awb
            if row['locked'] == '1' and row['calculated'] == '0':
                assert last_awb and last_awb['locked'] == '1'
                assert all(row[key] == last_awb[key] for key in ['red', 'blue']); held += 1
            awb[sof] = row; last_awb = row
        if 'WB context ' in line:
            sof = int(row['sof']); assert sof not in wb and row['known'] == '1'; wb[sof] = row
        if 'IPE_TONE_BOOTSTRAP ' in line:
            sof = int(row['sof']); assert sof not in boot
            assert row['ccm'] == ('1' if model == 'imx471' else '0'); boot[sof] = row
        if 'IPE_TONE_HOLD ' in line:
            token = int(row['token']); assert token not in holds; holds[token] = row
        if 'IPE_TONE_PREPARE ' in line:
            token = int(row['token']); observation = observations[token]
            cookie = int(row['gtm-cookie']); version = gtm[cookie]; ack = applied[cookie]
            assert all(row[key] == observation[key] for key in ['epoch', 'sof', 'gtm-cookie', 'gtm-generation'])
            assert row['gtm-generation'] == ack['generation'] and version['ready'] == '1'
            assert row['gtm-source-sof'] == version['source-sof'] and int(version['source-sof']) < int(row['sof'])
            assert int(ack['sof']) <= int(row['sof'])
            assert version['source-histogram'] == by_sof[int(version['source-sof'])]['trace'] == row['gtm-source-histogram']
            assert float(row['previous-ltm-lux']) == previous_lux
            assert observation['lux-valid'] == observation['gamma-override'] == '1' and row['bytes'] == '6008'
        if 'IPE_TONE_RECEIPT ' in line:
            token = int(row['token'])
            if row['success'] == '1': previous_lux = float(numeric[token]['lux'])
        if 'IPE_CCM_PREPARE ' in line:
            token = int(row['token']); observation = observations[token]
            assert model == 'imx471' and token not in ccm and row['manual'] == '0'
            assert row['sof'] == row['source-sof'] == observation['sof'] and row['isp-revision'] == observation['revision']
            ccm[token] = row
    for token, row in queues.items():
        sof = int(row['sof']); observation = observations[token]
        assert sof in pd10 and pd10[sof]['epoch'] == row['epoch'] == observation['epoch']
        assert row['bytes'] == '6008'
        if row['fresh'] == '0':
            if sof in boot:
                assert boot[sof]['cookie'] == observation['gtm-cookie'] and boot[sof]['generation'] == observation['gtm-generation']
            else:
                assert token in holds
    assert set(ccm) == (set(numeric) if model == 'imx471' else set())
    for sof in delivered:
        observation = by_sof[sof]
        assert sof in awb and sof in wb
        assert wb[sof]['epoch'] == awb[sof]['epoch'] == observation['epoch']
        assert wb[sof]['revision'] == observation['revision'] == awb[sof]['revision']
    math_delivered = sorted(int(observations[token]['sof']) for token, row in numeric_receipts.items()
                            if row['success'] == '1' and int(observations[token]['sof']) in delivered)
    assert math_delivered, 'No delivered successful mathematical IPE frame'
    return dict(same_sof_pd10_wb_gtm_history=True, delivered_math_sofs=math_delivered,
                first_twelve_delivered_math_sofs=[sof for sof in math_delivered if sof in sorted(delivered)[:12]],
                pd10_bytes=coarse_bytes, gtm_banks=sorted({int(row['bank']) for row in applied.values()}),
                ccm_domain='IPE' if model == 'imx471' else 'IFE', held_locked_wb_frames=held,
                ife_gtm_enabled=any(row['enabled'] == '1' for row in gtm.values()))
