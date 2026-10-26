"""Audit cached 476 control steps, including its retained failed zero-IPE contract.

No transport, target execution, SDK, or build entry point. Scene statistics stay
in the private output. A successful audit never changes the 476 worker result.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import re
import statistics
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
EXPOSURE, GAIN = 0x980911, 0x9e0903
SCHEDULE = [(12, EXPOSURE, 1200), (36, EXPOSURE, 500), (60, EXPOSURE, 1200),
            (84, GAIN, 128), (108, GAIN, 64), (132, GAIN, 128),
            (156, GAIN, 64), (180, EXPOSURE, 800), (204, EXPOSURE, 500)]
SOURCE_HASHES = {
    'camss_vfe-461.cpp': 'befec1da3743545652adc669cc649860d6840738e38a3798305d213b2e874b40',
    'camss-ipa6.cpp': 'd963f91d55b52b7693b73c6a05ad0ad282de47335592fb5c02821ddc9cb7520c',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def records(text, tag, fields):
    """Keep every tagged record, rejecting incomplete/duplicate field parsing."""
    rows = []
    pattern = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(tag) + r'(?=\s)')
    for line in text.splitlines():
        match = pattern.search(line)
        if not match:
            continue
        pairs = re.findall(r'([A-Za-z][A-Za-z0-9_-]*)=([^\s]+)', line[match.end():])
        values = dict(pairs)
        assert len(values) == len(pairs), (tag, 'duplicate field')
        assert set(values) == set(fields), (tag, set(values), set(fields))
        rows.append({key: cast(values[key]) for key, cast in fields.items()})
    return rows


def integer_records(text, tag, names):
    return records(text, tag, {key: int for key in names.split()})


def independent_steps(pairs, events, writes, quality=None):
    """306 windows/thresholds; no expected response offset is supplied."""
    means = {p['sof']: p['mean'] for p in pairs}
    timeline = {e['sequence']: e for e in events}
    quality = quality or {}
    previous = {EXPOSURE: 500, GAIN: 64}
    results = []
    for write in writes:
        n, control = write['sof'], write['id']
        prior = previous[control]
        direction = 'up' if write['value'] > prior else 'down'
        previous[control] = write['value']
        needed = set(range(n - 6, n)) | set(range(n, n + 8)) | set(range(n + 6, n + 14))
        missing_pairs = sorted(needed - means.keys())
        missing_events = sorted(needed - timeline.keys())
        reasons = []
        if missing_pairs:
            reasons.append('missing-paired-sof')
        if missing_events:
            reasons.append('missing-step-window-event')
        event = timeline.get(n)
        if not event or event['event_ns'] != write['event_ns'] or event['pending']:
            reasons.append('event-mismatch-or-pending')
        if write['ret'] or write['errno'] or not write['event_ns'] <= write['begin_ns'] <= write['end_ns']:
            reasons.append('failed-or-invalid-write')
        if n + 1 not in timeline or write['end_ns'] >= timeline[n + 1]['event_ns']:
            reasons.append('write-crossed-next-sof')
        if any(quality.get(str(s), {}).get('saturated') for s in needed):
            reasons.append('known-saturation')
        if any(means.get(s, 0) >= 1023 for s in needed):
            reasons.append('full-scale-mean')
        row = dict(step=write['step'], sof=n,
                   control='exposure' if control == EXPOSURE else 'analogue_gain',
                   direction=direction, prior_value=prior, value=write['value'],
                   write_start_after_sof_us=(write['begin_ns'] - write['event_ns']) / 1000,
                   write_duration_us=(write['end_ns'] - write['begin_ns']) / 1000,
                   write_finished_before_next_sof=(n + 1 in timeline and write['end_ns'] < timeline[n + 1]['event_ns']),
                   missing_paired_sofs=missing_pairs, missing_event_sofs=missing_events,
                   useful_response=False, first_observed_changed_offset=None,
                   first_three_frame_plateau_offset=None, invalid_reasons=reasons)
        if not reasons:
            pre = [means[s] for s in range(n - 6, n)]
            post = [means[s] for s in range(n + 6, n + 14)]
            left, right = statistics.median(pre), statistics.median(post)
            delta = right - left
            noise = max(statistics.median(abs(x - left) for x in pre),
                        statistics.median(abs(x - right) for x in post), 0.000001)
            adequate = abs(delta) > 10 * noise and abs(delta) > 0.05 * max(abs(left), abs(right))
            response = [(means[n + k] - left) / delta if delta else None for k in range(8)]
            first = next((k for k in range(6) if all(0.15 <= x <= 1.5 for x in response[k:k + 3])), None) if adequate else None
            plateau = next((k for k in range(6) if all(0.85 <= x <= 1.15 for x in response[k:k + 3])), None) if adequate else None
            row.update(pre_median=left, post_median=right, robust_noise=noise,
                       signal_to_robust_noise=abs(delta) / noise, normalized_response=response,
                       response_direction_agrees=(delta > 0) == (direction == 'up'),
                       passes_10x_noise=abs(delta) > 10 * noise,
                       passes_5_percent_response=abs(delta) > 0.05 * max(abs(left), abs(right)),
                       useful_response=adequate, first_observed_changed_offset=first,
                       first_three_frame_plateau_offset=plateau,
                       invalid_reasons=[] if adequate else ['original-low-snr-or-small-response'])
        results.append(row)
    return results


def audit(root, health_path, private, quality=None):
    state = json.loads((root / 'state.json').read_bytes())
    assert state['stage'] == 476 and state['terminal'] and state['phase'] == 'finished'
    assert state['passed'] is False
    failure = (root / 'failure.txt').read_text()
    assert failure == state['failure']
    assert failure.rstrip().endswith('AssertionError: Measurement profile must not schedule IPE jobs')
    assert "after['completed']==before['completed']" in failure
    archive = root.parent / 'runtime-collected-r1-private.tar.gz'
    assert archive.stat().st_size == 89918
    assert sha(archive) == '00f825783bb16d090161e51c402414d06a82383e7d7ccba863e2eb9b5ad13389'
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        assert len(members) == 29 and all(m.isfile() for m in members)
        assert len({m.name for m in members}) == 29
        for member in members:
            assert len(Path(member.name).parts) == 1
            assert stream.extractfile(member).read() == (root / member.name).read_bytes()
    frozen = json.loads((HERE.parent / 'kernel476/frozen-validation.json').read_bytes())
    for name, digest in frozen['files'].items():
        assert sha(HERE.parent / 'kernel476' / name) == digest, name
    spec = importlib.util.spec_from_file_location('frozen476', HERE.parent / 'kernel476/analyse-local.py')
    frozen_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen_module)
    manifest = json.loads((root / 'manifest.json').read_bytes())
    plan = json.loads((root / 'tele-plan-private.json').read_bytes())
    for name, digest in manifest.items():
        if (root / name).is_file():
            assert sha(root / name) == digest, name
    assert manifest['capture-body-tele.py'] == frozen['files']['capture-body-control.py']
    assert plan['deployable'] and plan['kind'] == 'sensor-control-delay'
    assert plan['no_ae'] and plan['no_delayed_controls'] and plan['delay_not_preset']
    assert plan['actual_sensor'] == [4208, 2368] and plan['expected_ll'] == 4848 and plan['expected_fll'] == 3312
    tool_report = json.loads((HERE.parent / 'kernel472/tools-build-validation.json').read_bytes())
    assert tool_report['passed']
    for row in tool_report['tools']:
        assert plan['common_payload'][Path(row['path']).name] == row['sha256']
        source = root.parent.parent / 'kernel472' / ('candidate-control-stepper.c' if row['label'] == 'stepper' else 'candidate-delay-capture.cpp')
        assert sha(source) == row['source_sha256']
    step_source = (root.parent.parent / 'kernel472/candidate-control-stepper.c').read_text()
    assert 'call(sensor,VIDIOC_G_CTRL,&readback)||readback.value!=c.value' in step_source
    assert step_source.index('call(sensor,VIDIOC_G_CTRL,&readback)') < step_source.index('applied++;')
    profile = root.parent / 'mode2-measurement-private.yaml'
    assert sha(profile) == plan['common_payload'][profile.name] == frozen['private_measurement_profile_sha256']
    assert not re.search(r'^\s*(sensor_controls|agc|awb|ipe|exposure_delay|gain_delay):', profile.read_text(), re.M)
    sources = {name: (private / 'retained-source' / name).read_text() for name in SOURCE_HASHES}
    for name, digest in SOURCE_HASHES.items():
        assert sha(private / 'retained-source' / name) == digest
    pipeline, ipa = sources['camss_vfe-461.cpp'], sources['camss-ipa6.cpp']
    assert 'if (d->processedEnabled_ && d->ipe_)' in pipeline
    assert pipeline.index('double(h.weightedSum) / h.population') < pipeline.index('ipe_->queue(buffer,output')
    assert 'result.weightedSum = parsed.weightedSum;' in ipa
    assert 'if (!ipeTone_) return 0;' in ipa and 'agc_.reset(); awb_.reset();' in ipa
    text = (root / 'control-capture-private.log').read_text()
    pairs = records(text, 'Pair', dict(epoch=int, sof=int, request=int, population=int, mean=float, **{'parameter-buffer-submitted': int}))
    events = integer_records(text, 'STEPPER_SOF', 'sequence pending event_ns observed_ns')
    writes = integer_records(text, 'CONTROL_WRITE', 'step sof id value event_ns begin_ns end_ns ret errno')
    frames = integer_records(text, 'APPLICATION_FRAME', 'number request sequence timestamp status bytes hash first_plane_min first_plane_max')
    contexts = integer_records(text, 'SensorContext', 'epoch sof valid exposure-lines gain-code source')
    observations = records(text, 'IPE_OBSERVE', {k: float if k in ['analogue-gain', 'exposure-index'] else int for k in
                           'epoch sof token trace population exposure-ns analogue-gain lines code source revision lux-valid exposure-index gamma-override gtm-cookie gtm-generation'.split()})
    ipe_pairs = records(text, 'IPE_PAIR', {k: float if k == 'analogue-gain' else int for k in 'epoch sof token trace exposure-ns analogue-gain'.split()})
    queues = integer_records(text, 'IPE_TONE_QUEUE', 'epoch sof token revision fresh bytes pd10 result')
    receipts = integer_records(text, 'IPE_RECEIPT', 'epoch sof token success result trace pending')
    histories = integer_records(text, 'IPE_HISTORY_STOP', 'epoch prepared committed discarded superseded aborted pending')
    cancellations = integer_records(text, 'REQUEST_STOP_CANCEL', 'epoch request raw')
    stats = integer_records(text, 'IPA stats', 'pid epoch sof status')
    awb = records(text, 'AWB_STATE', {k: float if k in ['red', 'blue'] else int for k in
                                    'epoch sof revision calculated regions locked red blue'.split()})
    errors = [line for line in text.splitlines() if ' ERROR ' in line]
    assert len(errors) == 1 and 'Failed to open configuration file "/root/.config/libcamera/configuration.yaml"' in errors[0]
    assert [x['sequence'] for x in events] == list(range(233))
    assert [x['step'] for x in writes] == list(range(9))
    assert [(x['sof'], x['id'], x['value']) for x in writes] == SCHEDULE
    assert all(x['pending'] == 0 and x['event_ns'] <= x['observed_ns'] for x in events)
    assert all(a['event_ns'] < b['event_ns'] for a, b in zip(events, events[1:]))
    assert all(events[w['sof']]['observed_ns'] <= w['begin_ns'] for w in writes)
    for rows in [pairs, observations, ipe_pairs, queues, receipts, stats]:
        assert [x['sof'] for x in rows] == list(range(240))
        assert all(x['epoch'] == 1 for x in rows)
    assert all(x['population'] == 2491136 and x['parameter-buffer-submitted'] == 1 and math.isfinite(x['mean']) and 0 <= x['mean'] <= 1023 for x in pairs)
    assert [x['request'] for x in pairs] == list(range(240))
    assert [x['number'] for x in frames] == [x['request'] for x in frames] == [x['sequence'] for x in frames] == list(range(240))
    assert all(x['status'] == 0 and x['bytes'] == 86400 and x['timestamp'] > 0 for x in frames)
    for observation, pair, queue, receipt in zip(observations, ipe_pairs, queues, receipts):
        assert observation['token'] == pair['token'] == queue['token'] == receipt['token'] == observation['sof'] + 1
        assert observation['trace'] == pair['trace'] == receipt['trace']
        assert all(observation[k] == 0 for k in ['revision', 'lux-valid', 'exposure-index', 'gamma-override', 'gtm-cookie', 'gtm-generation'])
        assert observation['lines'] == 500 and observation['code'] == 64 and observation['source'] == 0xffffffff
        assert all(queue[k] == 0 for k in ['revision', 'fresh', 'bytes', 'pd10', 'result'])
        assert receipt['success'] == receipt['result'] == 1 and receipt['pending'] == 0
    assert histories == [dict(epoch=1, prepared=240, committed=240, discarded=0, superseded=0, aborted=0, pending=0)]
    assert cancellations == [dict(epoch=1, request=n, raw=0) for n in range(240, 243)]
    assert all(x['status'] == 0 for x in stats)
    assert [x['sof'] for x in awb] == list(range(240))
    assert all(x['epoch'] == 1 and x['revision'] == x['calculated'] == x['regions'] == 0 and x['red'] == x['blue'] == 1 for x in awb)
    assert [x['sof'] for x in contexts] == list(range(241))
    assert all(x['valid'] == 1 and x['exposure-lines'] == 500 and x['gain-code'] == 64 for x in contexts)
    assert len(re.findall(r'Sensor configuration model=s5k3m5 pixel-rate=481930000 line-length=4848 frame-length=3312 delayed-controls=0 lsc=0 white-balance-reference=0', text)) == 2
    assert not re.search(r'(?:AGC_APPLY|Automatic sensor update|SENSOR_WRITE|AE update epoch=|Rejected AE update)', text)
    assert len(re.findall(r'STEPPER_MODE width=4208 height=2368 code=12298 crop=0,376,4208,2368 hblank=640 vblank=944 pixel_rate=481930000 test_pattern=0', text)) == 2
    for expected in ['STEPPER_RESULT result=0 events=233 steps=9', 'STEPPER_INITIAL_READBACK exposure=500 gain_code=64',
                     'APPLICATION_EPOCH epoch=0 frames=240 failed=0 stop=0', 'APPLICATION_RESULT result=0',
                     'FIXTURE_RESTORATION result=0', 'IPE enabled 320x180-NV12/sYCC requests=1 pd10=0']:
        assert text.count(expected) == 1, expected
    witness = json.loads((root / 'control-live-witness-private.json').read_bytes())
    assert witness['passed'] and witness['isolated'] and witness['old461_core_and_proxy']
    processes = witness['processes']
    assert len({x['pid'] for x in processes}) == 3 and all(x['start_ticks'] > 0 for x in processes)
    assert {x['program'] for x in processes} == {'delay-capture-mode2-aarch64', 'proxy/camss_ipa_proxy', 'control-stepper-mode2-aarch64'}
    assert {x['pid'] for x in processes if x['program'] == 'delay-capture-mode2-aarch64'} == set(map(int, re.findall(r'APPLICATION_PROCESS pid=(\d+)', text)))
    assert {x['pid'] for x in processes if x['program'] == 'proxy/camss_ipa_proxy'} == {x['pid'] for x in stats}
    assert {x['pid'] for x in processes if x['program'] == 'control-stepper-mode2-aarch64'} == set(map(int, re.findall(r'STEPPER_READY pid=(\d+)', text)))
    kernel = (root / 'kernel-log-private.txt').read_text()
    assert list(map(int, re.findall(r'A5 IPE frame completed request=(\d+)', kernel))) == list(range(1, 241))
    health = json.loads(health_path.read_bytes())
    assert health['health_audit']['passed'] and health['health_audit']['same_boot']
    assert health['health_audit']['taint'] == 0 and not any(health['health_audit']['fault_delta'].values())
    assert health['health_audit']['limits_unchanged'] and health['health_audit']['camera_and_four_services_unchanged']
    assert set(kernel.splitlines()) <= set(health['dmesg'].splitlines())
    assert state['sensor_module_restored'] and state['formal_modules_restored'] and state['services_restored']
    assert state['taint_after'] == 0 and not state['new_faults'] and state['tele_final_checks']['passed']
    assert state['tele_final_checks']['formal_library_equal'] and state['tele_final_checks']['formal_packages_equal']
    assert state['tele_final_checks']['no_user_processes_or_directory']
    assert all(v == 'suspended' for v in state['tele_final_checks']['camera_runtime'].values())
    steps = independent_steps(pairs, events, writes, quality)
    frozen_result = frozen_module.analyse(text, quality=quality)
    common_keys = ['step', 'sof', 'control', 'direction', 'value', 'useful_response', 'first_observed_changed_offset', 'first_three_frame_plateau_offset', 'invalid_reasons']
    assert [{k: r[k] for k in common_keys} for r in steps] == [{k: r[k] for k in common_keys} for r in frozen_result['changes']]
    periods = [b['event_ns'] - a['event_ns'] for a, b in zip(events, events[1:])]
    event_map = {e['sequence']: e for e in events}
    groups = {name: {direction: [r['step'] for r in steps if r['control'] == name and r['direction'] == direction and r['useful_response']]
                     for direction in ['up', 'down']} for name in ['exposure', 'analogue_gain']}
    public_steps = [{k: v for k, v in r.items() if k not in ['pre_median', 'post_median', 'robust_noise', 'normalized_response', 'signal_to_robust_noise']}
                    for r in steps]
    private_result = dict(stage=479, source_stage=476, events=events, writes=writes, paired_linear_bhist=pairs,
                          frames=frames, observations=observations, ipe_pairs=ipe_pairs, queues=queues,
                          raw_receipts=receipts, histories=histories, contexts=contexts, steps=steps,
                          original476_analysis=frozen_result, raw_log_error_lines=errors)
    public = dict(stage=479, source_stage=476, audit_passed=True, source_worker_passed=False,
                  original_worker_result_preserved=True, source_failure='Measurement profile must not schedule IPE jobs',
                  zero_ipe_contract_satisfied=False, actual_ipe_successful_receipts=240, kernel_ipe_completed_records=240,
                  ipe_history=histories[0], ipe_pd10=False, ipe_tone_bytes=0, ipe_revision=0,
                  default_processed_ipe_path_explains_contract_failure=True, startup_metadata_used_as_step_response=False,
                  application_frames=240, paired_linear_bhist_frames=240, stepper_sofs=233,
                  pipeline_sofs_including_stop=241, missing_stepper_sofs=[], missing_paired_sofs=[],
                  pending_events=sum(x['pending'] != 0 for x in events), failed_writes=sum(x['ret'] != 0 for x in writes),
                  raw_receipts=240, negative_receipts=0, stop_cancelled_requests=[240, 241, 242],
                  frame_period_ns=statistics.median(periods), expected_mode_period_ns=4848 * 3312 * 1e9 / 481930000,
                  write_start_after_sof_us_range=[min(r['write_start_after_sof_us'] for r in steps), max(r['write_start_after_sof_us'] for r in steps)],
                  write_duration_us_range=[min(r['write_duration_us'] for r in steps), max(r['write_duration_us'] for r in steps)],
                  write_completed_after_event_us_range=[min((w['end_ns'] - w['event_ns']) / 1000 for w in writes), max((w['end_ns'] - w['event_ns']) / 1000 for w in writes)],
                  write_next_sof_margin_min_us=min((event_map[w['sof'] + 1]['event_ns'] - w['end_ns']) / 1000 for w in writes),
                  event_observation_latency_us_range=[min((e['observed_ns'] - e['event_ns']) / 1000 for e in events), max((e['observed_ns'] - e['event_ns']) / 1000 for e in events)],
                  ae_disabled=True, delayed_controls_disabled=True, pre_ipe_bhist_response_independent=True,
                  explicit_initial_readback_records=1, per_step_readback_source_checked_on_success_path=True,
                  per_step_individual_readback_records=0, readback_is_v4l2_control_value_not_sensor_register_latch=True,
                  useful_steps=sum(r['useful_response'] for r in steps), per_control_direction=groups, steps=public_steps,
                  quality_sidecar_used=quality is not None, full_scale_mean_frames=sum(p['mean'] >= 1023 for p in pairs),
                  partial_clipping_ruled_out=False, no_delay_preset_or_profile_change=True,
                  hardware_register_or_full_frame_latch_proven=False, ipe_free_control_measurement_proven=False,
                  missing_optional_global_configuration_errors=1, formal_restore_and_external_health_verified=True,
                  source_hashes=SOURCE_HASHES,
                  collected_archive_files=29, collected_archive_bytes=archive.stat().st_size,
                  collected_archive_sha256=sha(archive),
                  evidence_sha256={name: sha(root / name) for name in ['state.json', 'failure.txt', 'control-capture-private.log', 'kernel-log-private.txt', 'manifest.json', 'tele-plan-private.json', 'control-live-witness-private.json']},
                  final_health_sha256=sha(health_path), frozen476_analyser_sha256=sha(HERE.parent / 'kernel476/analyse-local.py'),
                  inspector_sha256=sha(__file__), private_scene_values_published=False, phone_accessed=False, sdk_accessed=False)
    return public, private_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--health', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--quality', type=Path)
    args = parser.parse_args()
    quality = json.loads(args.quality.read_bytes()) if args.quality else None
    public, private_result = audit(args.root, args.health, args.private, quality)
    args.private.mkdir(parents=True, exist_ok=True)
    (args.private / 'control-analysis-private.json').write_text(json.dumps(private_result, indent=2) + '\n')
    (HERE / 'hardware-validation.json').write_text(json.dumps(public, indent=2) + '\n')
    print(json.dumps(dict(audit_passed=public['audit_passed'], source_worker_passed=public['source_worker_passed'],
                          useful_steps=public['useful_steps'], kernel_ipe_completed_records=public['kernel_ipe_completed_records'])))


if __name__ == '__main__':
    main()
