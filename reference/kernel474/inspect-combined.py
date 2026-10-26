"""Offline combined-core/proxy functional and 1080p LTM causality audit.

Reuse the frozen 471/473 strict frame, FULL-ring and Manager-capacity checks.
Native execution is established by observed identity, never by setting the
force-isolation variable to zero.  No phone, SDK or build operations occur.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import struct
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CORE = 'a21fcedde2f591f809a9c388a9a6ab78fa5072f33e06c91bbd55c8abf34cd97b'
PROXY = '35526054954ce43d1068c710f6be6d4cd172288e4da7ffcab677712815f08f4d'
IPA = '4c90047d42a91b9b1585d3b2cda997d8eee61f5e3a20f136b4345abcc2556d39'
SIGNATURE = 'f5c351bd947363791c072a7b9916adea00ec1a02c52671d7f9692aa735386205'
PROFILE = '6396ced1039e352a14c7a07187e780596a3a4180b22391bca0b30f7518db4094'
CLIENT = '7f4d6a1f8527280d8bbe11e6af638348200bd9bc8465be8357cdc0ca732b852a'
SENSOR = '494910c99ef116b88038ac3dfcc020a90aa35bfcc610b6b37c152601ee758392'
CASES = ['1920x1080-native', '1920x1080-isolated']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def retained_functions():
    manager_path = HERE.parent / 'kernel473/inspect-capacity-comparison.py'
    assert sha(manager_path) == 'e50df4bc7b9e4718ebcd4335501c1b955e58b49766a5c1905cd94a0c917e1e58'
    manager = load('manager473for474', manager_path)
    source = manager.adapted_source()

    def replace(before, after):
        nonlocal source
        assert source.count(before) == 1, (before, source.count(before))
        source = source.replace(before, after)

    replace('def inspect_case(case, expected_proxy, trace_events, full_role, summary, dependencies, expected_core=CORE, expected_capacity=False):',
            'def inspect_case(case, expected_proxy, trace_events, full_role, summary, dependencies, expected_core=CORE, expected_capacity=False, expected_isolated=True):')
    replace("    assert witness['passed'] and witness['isolated'] and witness['application']['exe_sha256'] == CLIENT",
            "    assert witness['passed'] and witness['isolated'] is expected_isolated and witness['application']['exe_sha256'] == CLIENT")
    replace("    assert witness['proxy_exe_sha256'] == expected_proxy",
            "    if expected_isolated:\n        assert witness['proxy_exe_sha256'] == expected_proxy and witness['ipa_pid'] != witness['application']['pid']\n        assert witness['force_isolation_env'] == '1'\n    else:\n        assert witness['proxy_exe_sha256'] is None and witness['ipa_pid'] == witness['application']['pid']\n        assert witness['force_isolation_env'] is None")
    replace('actual_proc_exe_verified=True, strict=strict_result,',
            'actual_process_core_ipa_identity_verified=True, proxy_executed=expected_isolated, actual_proxy_exe_verified=expected_isolated, native_ipa_same_process_verified=not expected_isolated, strict=strict_result,')
    replace("    mathematical = frame_rows[3:]\n    assert len(mathematical) == 29 and all('IPE_TONE_PREPARE' in r for r in mathematical)\n    assert all('IPE_TONE_BOOTSTRAP' in r for r in frame_rows[:3])",
            "    mathematical = [r for r in frame_rows if 'IPE_TONE_PREPARE' in r]\n    bootstrap_frames = [r for r in frame_rows if 'IPE_TONE_BOOTSTRAP' in r]\n    assert len(mathematical) == strict_result['successful_math'] and len(bootstrap_frames) == strict_result['bootstrap']\n    assert len(mathematical) + len(bootstrap_frames) == len(frame_rows) and all(('IPE_TONE_PREPARE' in r) != ('IPE_TONE_BOOTSTRAP' in r) for r in frame_rows)")
    replace('consumed=32, successful_math_samples=29,', 'consumed=32, successful_math_samples=len(mathematical), bootstrap_consumed=len(bootstrap_frames),')
    before = '''        assert sof > samples[-1][6] and sof not in queued_sofs
        assert by_sof[sof].get('IPE_TONE_PREPARE')
        assert stop_times and min(stop_times) <= by_sof[sof]['IPE_RECEIPT'][0]['ns']
        negative_stop.append(dict(sof=sof, mathematical_prepare_logged=True,
                                  ipe_queue_logged=False, returned_after_stop_cancel=True,
                                  counted_as_consumed_or_physical_ipe=False))
    assert strict_result['discarded_unqueued_observations'] == len(negative_stop)'''
    after = '''        assert sof not in {sample[6] for sample in samples}
        after_stop = bool(stop_times and min(stop_times) <= by_sof[sof]['IPE_RECEIPT'][0]['ns'])
        negative_stop.append(dict(sof=sof, mathematical_prepare_logged=bool(by_sof[sof].get('IPE_TONE_PREPARE')),
                                  ipe_queue_logged=sof in queued_sofs, returned_after_stop_cancel=after_stop,
                                  counted_as_consumed=False))
    assert strict_result['discarded_unqueued_observations'] == sum(not row['ipe_queue_logged'] for row in negative_stop)'''
    replace(before, after)
    source = source.replace('negative_unqueued_stop_observations=negative_stop', 'negative_observations=negative_stop')
    namespace = dict(__name__='retained471_473_for474', __file__=str(HERE / 'inspect-combined.py'),
                     NEW_CORE=CORE, manager_capacity=manager.manager_capacity)
    exec(compile(source, 'retained471_473-native-isolated-combined474', 'exec'), namespace)
    return namespace, hashlib.sha256(source.encode()).hexdigest()


def fnv(data):
    value = 1469598103934665603
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return value


def inspect_ltm(run, state):
    source = run / '1920x1080-isolated'
    replay_dir = run / '1920x1080-replay'
    text = (source / 'client.log').read_text()
    traces = re.findall(r'IPE_TONE_TRACE epoch=(\d+) sof=(\d+) token=(\d+) revision=(\d+) full-sequence=(\d+) pd10-sequence=(\d+) result=(-?\d+)', text)
    assert len(traces) == 1
    epoch, sof, token, revision, full_sof, pd10_sof, status = map(int, traces[0])
    assert epoch == 1 and sof == full_sof == pd10_sof and sof >= 12 and revision > 0 and status == 0
    assert len(re.findall(r'IPE_TONE_QUEUE epoch=1 sof=' + str(sof) + r' token=' + str(token)
                          + r' revision=' + str(revision) + r' fresh=1 bytes=6008 pd10=1 result=0', text)) == 1
    assert len(re.findall(r'IPE_RECEIPT epoch=1 sof=' + str(sof) + r' token=' + str(token)
                          + r' success=1 result=1 ', text)) == 1
    assert 'IPE_TONE_TRACE ' not in (run / '1920x1080-native/client.log').read_text()
    saved = state['replays']['1920x1080']
    assert saved['passed'] and saved['ipe_completed'] == 4
    assert (saved['source_sof'], saved['epoch'], saved['token'], saved['revision']) == (sof, epoch, token, revision)
    originals = {}
    for name, suffix, length in [('full-private.bin', '-full.nv12', 3110400),
                                 ('pd10-private.bin', '-coarse.pd10', 261120),
                                 ('parameters-private.bin', '-params.bin', 6008)]:
        data = (replay_dir / name).read_bytes()
        assert len(data) == length and data == (source / 'captures' / f'tone-{sof}{suffix}').read_bytes()
        originals[name] = data
    full, coarse, params = (originals[name] for name in ['full-private.bin', 'pd10-private.bin', 'parameters-private.bin'])
    assert struct.unpack_from('<II', params) == (1, 6008)
    outputs = [(replay_dir / f'mode-{i}-output-private.bin').read_bytes() for i in range(4)]
    assert all(len(data) == 3110400 for data in outputs)
    assert outputs[0] == outputs[3] and len(set(outputs[:3])) == 3
    log_path = replay_dir / 'client.log'
    replay_log = log_path.read_text()
    assert 'PD10_IPE_RESULT result=0 frames=4' in replay_log
    jobs = [json.loads(line) for line in replay_log.splitlines() if line.startswith('{')]
    assert jobs == saved['jobs'] and [job['mode'] for job in jobs] == [0, 1, 2, 3]
    # The retained 441 quarter geometry: 480 x 270, 1920-byte packed rows,
    # 136 allocated rows.  Alter only the 135 x 240 active eight-byte groups.
    hashes = []
    for mode, job in enumerate(jobs):
        expected = bytearray(coarse)
        if mode in [1, 2]:
            y = 0 if mode == 1 else 255
            word = bytes([y] * 4 + [128, 128, y, 0])
            for row in range(135):
                for group in range(240):
                    offset = row * 1920 + group * 8
                    expected[offset:offset + 8] = word
        assert job['passed'] and job['full_hash'] == f'{fnv(full):016x}'
        assert job['pd10_hash'] == f'{fnv(expected):016x}'
        assert job['output_hash'] == f'{fnv(outputs[mode]):016x}'
        scratch = (replay_dir / f'mode-{mode}-scratch-private.bin').read_bytes()
        assert len(scratch) == 261168 + 16
        version, length, crc, changed = struct.unpack_from('<IIII', scratch)
        assert (version, length, crc, changed) == (1, 261168, job['scratch_crc'], job['scratch_changed_bytes'])
        hashes.append(dict(mode=mode, output_sha256=hashlib.sha256(outputs[mode]).hexdigest(),
                           scratch_crc=crc, scratch_changed_bytes=changed))
    sample = re.findall(r'GST_IMAGE frame=\d+ width=1920 height=1080 bytes=3110400 pts=\d+ hash=(\d+) sequence='
                        + str(sof) + r' wall-ns=\d+', text)
    assert len(sample) == 1
    assert int(sample[0]) == fnv(outputs[0][::max(1, len(outputs[0]) // 4096)])
    assert saved['source_consumed_sample_hash_equal'] and not saved['source_output_full_byte_compare']
    return dict(width=1920, height=1080, source_sof=sof, source_epoch=epoch, source_token=token, source_revision=revision,
                replay_order=['real', 'black', 'white', 'same-real'], physical_ipe_completed=4,
                full_and_parameters_byte_fixed=True, source_full_pd10_and_final_params_snapshots_equal=True,
                independently_constructed_black_white_pd10_hashes_match=True,
                three_distinct_complete_nv12_outputs=True, real_repeat_full_byte_equal=True,
                consumer_sample_hash_matches_real_replay=True, consumer_full_byte_comparison_performed=False,
                scratch_changed_bytes=[job['scratch_changed_bytes'] for job in jobs],
                scratch_crc_varied=len({job['scratch_crc'] for job in jobs}) > 1,
                scratch_mutation_used_as_consumption_evidence=False, outputs=hashes,
                input_sha256={name: hashlib.sha256(data).hexdigest() for name, data in originals.items()},
                replay_log_sha256=sha(log_path), passed=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run-root', type=Path)
    parser.add_argument('--health', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    retained, case_audit_sha = retained_functions()
    dependencies = retained['modules']()
    if args.self_test:
        private = Path('E:/edk2-samurai-out') if Path('E:/').exists() else Path('/mnt/e/edk2-samurai-out')
        log = private / 'kernel468/runtime-collected-r2/1920x1080-isolated/client.log'
        row = dependencies[3](log.read_text(), 's5k3m5', width=1920, height=1080, stride=1920, coarse_bytes=261120)
        assert row['frames'] == 32 and row['successful_math'] == 29
        result = dict(stage=474, tool_self_test_passed=True, actual474_hardware_examined=False,
                      retained_strict_frames=32, adapted_case_auditor_sha256=case_audit_sha,
                      ltm_1080_actual_pending=True)
        (HERE / 'combined-tool-validation.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        return
    assert args.run_root and args.health
    run = args.run_root
    state = json.loads((run / 'state.json').read_bytes())
    plan = json.loads((run / 'tele-plan-private.json').read_bytes())
    handoff = json.loads((run / 'handoff-private.json').read_bytes())
    proof = json.loads((run / 'proof.json').read_bytes())
    assert state['terminal'] and state['passed'] and not state['failure'] and not state.get('cleanup_failure')
    assert state['formal_modules_restored'] and state['sensor_module_restored'] and state['services_restored'] and state['tele_final_checks']['passed']
    assert state['taint_before'] == state['taint_after'] == 0 and not state['new_faults']
    assert state['tele_charging_before'] == state['tele_charging_after'] == handoff['charging']
    assert plan['cases'] == CASES and plan['sensor_mode'] == 2 and plan['actual_sensor'] == [4208, 2368]
    assert plan['combined_payload_fixed'] and plan['full_ring_enabled_all_segments']
    assert [s['name'] for s in plan['segments']] == CASES
    assert [s['isolated'] for s in plan['segments']] == [False, True]
    assert all(s['core_sha256'] == CORE and s['proxy_sha256'] == PROXY and s['expected_capacity_active']
               for s in plan['segments'])
    common = plan['common_payload']
    for name, expected in [('lib/libcamera.so.0.7.2', CORE), ('proxy/camss_ipa_proxy', PROXY),
                           ('factory-s5k3m5-private.yaml', PROFILE), ('gst-sustained', CLIENT)]:
        assert common[name] == expected
    assert IPA in common.values() and SIGNATURE in common.values()
    assert json.loads((run / 'manifest.json').read_bytes())['pd10-ipe'] == '5be7faeb481c68996e57f476889f5e51d1af550922d0c0ba809b6b5c5daac5f2'
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
    events = dependencies[0].parse_trace(trace)
    emission = guard.role.check_emission(trace_plan.full_role, [dict(event, event=event['kind']) for event in events])
    assert emission == state['full_emission']
    stats = []
    for file in sorted(evidence.glob('stats-private-1-cpu*.txt')):
        values = dict(re.findall(r'^([^:\n]+):\s*(.+)$', file.read_text(), re.M))
        parsed = {key: int(values[key]) for key in ['overrun', 'commit overrun', 'dropped events']}
        assert not any(parsed.values())
        stats.append(parsed)
    assert len(stats) == 8
    reports, times = [], []
    for name, isolated in zip(CASES, [False, True]):
        assert state['sustained'][name]['isolated'] is isolated
        report, frame_times = retained['inspect_case'](run / name, PROXY, events, trace_plan.full_role,
            state['sustained'][name], dependencies, expected_core=CORE, expected_capacity=True, expected_isolated=isolated)
        report.update(isolated=isolated, core_sha256=CORE, force_isolation_environment='1' if isolated else None)
        reports.append(report)
        times.append(dict(case=name, frames=frame_times))
    ltm = inspect_ltm(run, state)
    live_ipe = sum(case['ipe_completed'] for case in state['sustained'].values())
    final = state['candidate_final_status']
    assert final['jobs'] == final['completed'] == final['direct_completed'] == live_ipe + 4
    assert not any(final[key] for key in ['failed', 'cancelled', 'first_error', 'fatal', 'pinned', 'orphans', 'users', 'running'])
    health = json.loads(args.health.read_bytes())
    assert health['health_audit']['passed'] and health['health_audit']['manifest_sha256'] == handoff['charging']['manifest_sha256']
    for key in ['external_worker_exit_verified', 'formal_notes_verified', 'trace_instance_absent',
                'actual_restored_uid10000_services_verified', 'user_directory_absent']:
        assert health[key]
    log = (run / 'kernel-log-private.txt').read_text()
    assert log.strip() and all(line in health['dmesg'] for line in log.splitlines())
    (args.health.parent / 'combined-frame-times-private.json').write_text(json.dumps(times, indent=2) + '\n')
    result = dict(stage=474, passed=True, consumed=64, live_ipe_completed=live_ipe, replay_ipe_completed=4,
                  physical_ipe_completed=live_ipe + 4, successful_math_samples=sum(r['successful_math_samples'] for r in reports),
                  bootstrap_consumed=sum(r['bootstrap_consumed'] for r in reports),
                  raw_receipts=sum(r['raw_receipts'] for r in reports), negative_observation_receipts=sum(r['negative_receipts'] for r in reports),
                  negative_unqueued_after_stop_receipts=sum(not n['ipe_queue_logged'] and n['returned_after_stop_cancel'] for r in reports for n in r['negative_observations']),
                  successful_full_dq=sum(r['full_ring_successful_dq'] for r in reports),
                  successful_full_not_consumed=sum(r['successful_full_not_consumed'] for r in reports),
                  cases=reports, ltm_1080=ltm, full_ioctl_emission=emission,
                  adapted_case_auditor_sha256=case_audit_sha, reused_strict_auditor_sha256=dependencies[4],
                  raw_receipts_filtered=False, dynamic_manager_capacity_and_restore_verified_both_paths=True,
                  native_same_process_ipa_observed_without_forced_zero=True, isolated_proxy_exe_verified=True,
                  bounded_rings_and_actual_full_fds_both_paths=True, trace_overrun_commit_drop_all_zero=True,
                  formal_restore_and_external_health_verified=True, goal_complete=False,
                  steady_zero_gap_power_optical_or_all_camera_acceptance=False,
                  initial_fixed_three_bootstrap_timing_assumption_rejected=True,
                  timing_samples_classified_from_actual_unfiltered_history=True,
                  inputs_sha256=dict(state=sha(run / 'state.json'), plan=sha(run / 'tele-plan-private.json'),
                                     trace=sha(trace), health=sha(args.health)))
    (HERE / 'hardware-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(stage=474, passed=True, consumed=64, physical_ipe=live_ipe + 4,
                         gap_counts=[len(r['gaps']) for r in reports], ltm_1080_causal_passed=True)))


if __name__ == '__main__':
    main()
