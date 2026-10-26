"""Adapt the frozen 471 cached audit to a Manager-capacity-only A/B/A.

No device, SDK, build or shared-source access.  The old worker proxy is fixed
in all three segments; only B uses the 473 core's expanded acquisition gate.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE_SHA = 'b591ae93c06bf2230161b676788c649ba7ddfb11788b9d6a7e5cf4bb357428b3'
NEW_CORE = 'a21fcedde2f591f809a9c388a9a6ab78fa5072f33e06c91bbd55c8abf34cd97b'


def cpus(value):
    if value in [None, '', 'none']:
        return set()
    assert isinstance(value, str)
    result = set()
    for token in value.strip().split(','):
        bounds = token.split('-')
        assert len(bounds) in [1, 2] and all(re.fullmatch(r'\d+', part) for part in bounds)
        start, end = int(bounds[0]), int(bounds[-1])
        assert 0 <= start <= end < 1024
        result.update(range(start, end + 1))
    return result


def manager_capacity(text, witness, expected_active):
    actual = witness['manager_capacity']
    tids = {int(p) for p in re.findall(r'\] \[(\d+)\] +(?:INFO|DEBUG|WARN|ERROR) CamssVfe ', text)}
    assert len(tids) == 1 and actual['tid'] in tids and actual['start_ticks'] > 0
    assert actual['active'] is expected_active
    allowed = cpus(actual['actual_cpus_allowed_list'])
    assert allowed
    starts = re.findall(r'CAPACITY_START epoch=1 tid=(\d+) status=(-?\d+) reason=(\S+) active=([01]) users=(\d+) original=(\S+) selected=(\S+)', text)
    stops = re.findall(r'CAPACITY_STOP epoch=1 tid=(\d+) status=(-?\d+) reason=(\S+) active=([01]) users=(\d+) original=(\S+) selected=(\S+)', text)
    assert len(stops) == 1
    if expected_active:
        assert len(starts) == 1
        tid, status, reason, active, users, original, selected = starts[0]
        assert int(tid) == actual['tid'] and (status, reason, active, users) == ('0', 'selected', '1', '1')
        original_set, selected_set = cpus(original), cpus(selected)
        assert selected_set and selected_set < original_set
        assert cpus(actual['original']) == original_set and cpus(actual['selected']) == selected_set
        assert allowed == selected_set
        stop_tid, stop_status, stop_reason, stop_active, stop_users, stop_original, stop_selected = stops[0]
        assert int(stop_tid) == actual['tid']
        assert (stop_status, stop_reason, stop_active, stop_users) == ('0', 'restored', '0', '0')
        assert cpus(stop_original) == original_set and cpus(stop_selected) == selected_set
        capacities = actual.get('cpu_capacity')
        dynamic_selection_checked = False
        if capacities is not None:
            values = {int(cpu): int(value) for cpu, value in capacities.items()}
            assert original_set <= set(values) and all(values[cpu] > 0 for cpu in original_set)
            minimum = min(values[cpu] for cpu in original_set)
            higher = {cpu for cpu in original_set if values[cpu] > minimum}
            assert selected_set == higher
            dynamic_selection_checked = True
        return dict(active=True, actual_manager_tid_matches_pipeline=True,
                    during_proc_mask_matches_selected=True, original_cpus=sorted(original_set), selected_cpus=sorted(selected_set),
                    current_allowed_cpus=sorted(allowed), stop_status=0, stop_reason='restored',
                    stop_original_and_selected_masks_match=True,
                    restore_readback_from_unchanged448_helper=True,
                    external_poststop_proc_probe=False, dynamic_capacity_values_checked=dynamic_selection_checked,
                    cpu_capacity=actual.get('cpu_capacity'),
                    worker_affinity_or_cpu_inferred=False)
    assert not starts and stops[0] == ('0', '0', 'inactive', '0', '0', 'none', 'none')
    assert cpus(actual['original']) == cpus(actual['selected']) == allowed
    return dict(active=False, actual_manager_tid_matches_pipeline=True,
                current_allowed_cpus=sorted(allowed), stop_status=0, stop_reason='inactive',
                cpu_capacity=actual.get('cpu_capacity'),
                external_poststop_proc_probe=False, worker_affinity_or_cpu_inferred=False)


def adapted_source():
    path = HERE.parent / 'kernel471/inspect-comparison.py'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == BASE_SHA
    source = raw.decode()

    def replace(before, after):
        nonlocal source
        assert source.count(before) == 1, (before, source.count(before))
        source = source.replace(before, after)

    replace('def inspect_case(case, expected_proxy, trace_events, full_role, summary, dependencies):',
            'def inspect_case(case, expected_proxy, trace_events, full_role, summary, dependencies, expected_core=CORE, expected_capacity=False):')
    replace("    assert re.search(r'CAPACITY_STOP epoch=1 .* reason=inactive active=0 users=0 ', text)\n    assert 'CAPACITY_START ' not in text and 'FOCUS_TIMING ' not in text",
            "    assert 'FOCUS_TIMING ' not in text")
    replace("    assert witness['proxy_exe_sha256'] == expected_proxy",
            "    assert witness['proxy_exe_sha256'] == expected_proxy\n    assert witness['core_file_sha256'] == expected_core\n    capacity_result = manager_capacity(text, witness, expected_capacity)")
    replace('lsc_contexts_consistent=32, capacity_active=False, metrics=metrics, gaps=gaps,',
            'lsc_contexts_consistent=32, capacity_active=expected_capacity, manager_capacity=capacity_result, core_sha256=expected_core, metrics=metrics, gaps=gaps,')
    replace("    last_cpu = kernel_dq[-1]['cpu']",
            "    if expected_capacity:\n        assert {e['cpu'] for e in kernel_ioctls} <= set(capacity_result['selected_cpus'])\n    last_cpu = kernel_dq[-1]['cpu']")
    replace("    assert [s['proxy_sha256'] for s in plan['segments']] == [OLD, NEW, OLD]",
            "    assert [s['proxy_sha256'] for s in plan['segments']] == [OLD, OLD, OLD]\n    assert [s['core_sha256'] for s in plan['segments']] == [CORE, NEW_CORE, CORE]\n    assert [s['expected_capacity_active'] for s in plan['segments']] == [False, True, False]")
    replace('    for name, proxy in zip(CASES, [OLD, NEW, OLD]):',
            '    for name, proxy in zip(CASES, [OLD, OLD, OLD]):')
    replace("                                           state['sustained'][name], dependencies)",
            "                                           state['sustained'][name], dependencies,\n                                           expected_core=plan['segments'][CASES.index(name)]['core_sha256'],\n                                           expected_capacity=plan['segments'][CASES.index(name)]['expected_capacity_active'])")
    replace("    assert args.run_root and args.health", "    assert args.run_root and args.health\n    build = json.loads((HERE / 'build-validation.json').read_bytes())\n    assert build['passed'] and build['sdk_bind_unmounted'] and build['completion_ownership_fix_retained']\n    assert next(r['sha256'] for r in build['runtime_files'] if r['name'] == 'libcamera.so.0.7.2') == NEW_CORE")
    replace("    assert plan['common_payload']['lib/libcamera.so.0.7.2'] == CORE",
            "    assert plan['common_payload']['lib/libcamera.so.0.7.2'] == CORE\n    assert plan['common_payload']['proxy/camss_ipa_proxy'] == OLD\n    assert plan['only_core_gate_varies'] and plan['full_ring_enabled_all_segments']\n    source_check = json.loads((HERE / 'source-validation.json').read_bytes())\n    assert source_check['passed'] and source_check['only_one_source_changed'] and source_check['completion_ownership_fix_retained']\n    assert source_check['capacity_helper_sha256'] == '5801d89dcd326873df9d518df5a2667e5deeacf87bd0274bd1a241569bc9a463'")
    replace("    capacity_path = private.parent / 'kernel448/charging-baseline-private.json'\n    capacities = json.loads(capacity_path.read_bytes())['cpu_capacity']\n    assert set(capacities) == {str(i) for i in range(8)}",
            "    capacity_path = run / 'B-new/live-witness-private.json'\n    capacities = json.loads(capacity_path.read_bytes())['manager_capacity']['cpu_capacity']\n    assert capacities and all(int(v) > 0 for v in capacities.values())\n    for report in reports:\n        own = report['manager_capacity']['cpu_capacity']\n        assert all(capacities[cpu] == value for cpu, value in own.items())")
    source = source.replace('historical_capacity_group_ioctl_counts', 'fresh_capacity_group_ioctl_counts')
    source = source.replace("source='kernel448/charging-baseline-private.json'", "source='B-new/live-witness-private.json:manager_capacity.cpu_capacity'")
    source = source.replace('historical_only=True,', 'historical_only=False, fresh_capacity_values_available=True,')
    source = source.replace('stage=471', 'stage=473')
    source = source.replace('actual471_hardware_examined=False', 'actual473_hardware_examined=False')
    source = source.replace('pending_actual471=True', 'pending_actual473=True')
    source = source.replace("HERE / 'analysis-tool-validation.json'", "HERE / 'capacity-comparison-tool-validation.json'")
    source = source.replace("HERE / 'analysis-validation.json'", "HERE / 'hardware-validation.json'")
    source = source.replace('production_proxy_permanently_changed=False,',
                            'production_core_permanently_changed=False, old_proxy_fixed_all_segments=True,')
    source = source.replace('fresh471_capacity_frequency_or_worker_cpu_sample_available=False',
                            'fresh473_frequency_or_worker_cpu_sample_available=False')
    return source


if __name__ == '__main__':
    namespace = dict(__name__='__main__', __file__=str(HERE / 'inspect-capacity-comparison.py'),
                     NEW_CORE=NEW_CORE, manager_capacity=manager_capacity)
    exec(compile(adapted_source(), 'retained471-manager-capacity-comparison473', 'exec'), namespace)
