"""Affected IRQ/cohort functions only; saved old raw and explicit synthetic IRQs."""
from pathlib import Path
import ast
import base64
import copy
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda b: hashlib.sha256(b).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    m = load('actual_irq_cohort_device', HERE / 'device.py')
    f = load('saved_502_fixture', HERE.parent / 'image502-postboot-readonly/fixture.py')
    cohort_leaf = REF / 'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate'
    cohort = json.loads((cohort_leaf / 'cohort-manifest.json').read_bytes())
    manifest = json.loads((cohort_leaf / 'manifest.json').read_bytes())
    raw = f.facts()
    original_raw = copy.deepcopy(raw)
    raw['boot_partition']['sha256'] = m.IRQ_BOOT
    raw['manifest']['sha256'] = m.COHORT_MANIFEST
    raw['manifest_text'] = json.dumps(manifest)
    for name, item in cohort['modules'].items():
        target = manifest['modules'][name]['target']
        raw['installed_files'][target]['sha256'] = item['new']['sha256']
        fact = raw['charging_modules'][name]
        fact.update(sha256=item['new']['sha256'], disk_note_sha256=item['new']['resident_note_sha256'],
                    loaded_note_sha256=item['new']['resident_note_sha256'], loaded_note_matches_disk=True)
    raw['started_boottime_ns'], raw['ended_boottime_ns'] = 1, 100
    location = '/sys/devices/platform/soc@0/c440000.spmi/spmi-0/0-02/1300.usb-input'
    report = '           CPU0       CPU1\n 47: 0 0 pmic_arb 135940 Edge usbin-plugin\n 48: 0 0 pmic_arb 135942 Edge usbin-src-change\nIPI0: 9 8 Rescheduling interrupts\n'
    def snapshot(start, end):
        return {'started_boottime_ns': start, 'ended_boottime_ns': end, 'device': location,
                'driver': 'samurai-usb-input', 'of_node': m.NODE, 'bound_providers': [location],
                'properties_b64': {key: base64.b64encode(value).decode() for key, value in m.PROPERTIES.items()},
                'proc_interrupts': report}
    raw['irq_before'], raw['irq_after'] = snapshot(2, 3), snapshot(98, 99)
    identity = raw['identity_before']
    guard = {'boot_id': '00000000-0000-0000-0000-000000000501',
             'kernel_release': identity['uname']['release'], 'rootfs_release_sha256': identity['rootfs']['sha256'],
             'soc_serial_sha256': identity['serial_sha256'], 'compatible_sha256': sha(base64.b64decode(identity['compatible_b64']))}
    camera = json.loads(Path('/mnt/e/edk2-samurai-out/kernel481/formal-expected-private.json').read_bytes())
    request = {'guard': guard, 'camera': camera}
    cases = []
    assert m.audit(raw, request)['passed']
    assert not m.check_postboot(raw)['IRQ_delivery_or_icon_latency_accepted']
    cases.append('complete synthetic native-provider/cohort boot audit; zero counts are registration only')
    assert not any(m.delta(raw['irq_before'], raw['irq_after'])['positive_counts'].values())
    cases.append('registered zero counters do not imply delivery')
    increasing = copy.deepcopy(raw['irq_after'])
    increasing['proc_interrupts'] = report.replace('47: 0 0', '47: 2 3').replace('48: 0 0', '48: 0 1')
    counts = m.delta(raw['irq_before'], increasing)
    assert counts['comparable'] and counts['increments']['usbin-plugin']['sum'] == 5
    assert counts['positive_counts'] == dict.fromkeys(m.NAMES, True) and not counts['physical_delivery_accepted']
    cases.append('per-CPU monotonic count differences remain separate from physical causality')

    def reject(label, callback):
        try:
            callback()
        except (AssertionError, ValueError, KeyError):
            cases.append(label)
        else:
            raise AssertionError(label)

    reject('old R8 manifest/notes refused', lambda: m.check_install(original_raw))
    reject('old native boot refused', lambda: m.check_partitions(original_raw))
    for name in cohort['modules']:
        bad = copy.deepcopy(raw)
        bad['charging_modules'][name]['loaded_note_sha256'] = cohort['modules'][name]['old']['resident_note_sha256']
        reject('old resident ' + name + ' refused', lambda: m.check_install(bad))
    bad = copy.deepcopy(raw)
    changed = json.loads(bad['manifest_text'])
    del changed['installed_files']['/usr/sbin/samurai-charging']
    bad['manifest_text'] = json.dumps(changed)
    reject('manifest text cannot omit a retained file despite pinned file_fact', lambda: m.check_install(bad))
    for label, text in [
        ('one IRQ absent', report.replace(' 48: 0 0 pmic_arb 135942 Edge usbin-src-change\n', '')),
        ('both IRQs absent; polling-only load', ' CPU0 CPU1\nIPI0: 0 0 test\n'),
        ('duplicate IRQ name', report + ' 49: 0 0 pmic_arb 123 Edge usbin-plugin\n'),
        ('same IRQ number', report.replace('48:', '47:')),
        ('shared action', report.replace('Edge usbin-plugin', 'Edge other, usbin-plugin')),
        ('truncated CPU counters', report.replace('47: 0 0', '47: 0')),
        ('non-numeric counter', report.replace('47: 0 0', '47: x 0')),
        ('invalid CPU header', report.replace('CPU1', 'CPU0')),
        ('zero IRQ mapping', report.replace('47:', '0:')),
        ('counter overflow', report.replace('47: 0 0', '47: 18446744073709551616 0')),
    ]:
        reject(label, lambda text=text: m.parse_interrupts(text))
    for label, change in [
        ('legacy software provider', lambda d: d.update(of_node='/sys/firmware/devicetree/base/old')),
        ('duplicate provider', lambda d: d['bound_providers'].append('/sys/devices/platform/duplicate')),
        ('wrong native IRQ tuples', lambda d: d['properties_b64'].update(interrupts=base64.b64encode(b'wrong').decode())),
        ('reversed snapshot time', lambda d: d.update(started_boottime_ns=100)),
    ]:
        bad = copy.deepcopy(raw['irq_before'])
        change(bad)
        reject(label, lambda: m.validate_snapshot(bad))
    for label, text in [
        ('CPU hotplug makes totals incomparable', report.replace('CPU0       CPU1', 'CPU0').replace('47: 0 0', '47: 0').replace('48: 0 0', '48: 0')),
        ('IRQ remapping incomparable', report.replace('47:', '49:')),
    ]:
        bad = copy.deepcopy(raw['irq_after'])
        bad['proc_interrupts'] = text
        assert not m.delta(raw['irq_before'], bad)['comparable']
        cases.append(label)
    regressed = copy.deepcopy(increasing)
    regressed['started_boottime_ns'], regressed['ended_boottime_ns'] = 101, 102
    regressed['proc_interrupts'] = report
    assert not m.delta(increasing, regressed)['comparable']
    cases.append('per-CPU counter regression refused for delta')
    bad = copy.deepcopy(raw)
    bad['irq_after']['ended_boottime_ns'] = 101
    reject('snapshots outside collector interval refused', lambda: m.check_postboot(bad))
    bad = copy.deepcopy(raw)
    bad['irq_after']['proc_interrupts'] = report.replace('47:', '49:')
    assert not m.audit(bad, request)['passed']
    cases.append('native registration failure prevents whole postboot pass')
    old_source = (HERE.parent / 'image502-postboot-readonly/device.py').read_text()
    source = (HERE / 'device.py').read_text()
    funcs = lambda text: {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
    before, after = funcs(old_source), funcs(source)
    unchanged = {n: sha(s.encode()) for n, s in before.items() if after.get(n) == s}
    assert len(unchanged) == 21
    tree = ast.parse(source)
    forbidden = {'write_text', 'write_bytes', 'write', 'writelines', 'system', 'Popen', 'mkdir', 'unlink', 'remove'}
    assert not any(isinstance(node, ast.Attribute) and node.attr in forbidden for node in ast.walk(tree))
    assert all(word not in source for word in ('/dev/mem', 'O_RDWR', 'PROT_WRITE'))
    local = subprocess.run(['python3', '-B', str(HERE / 'device.py'), '--check-local'], capture_output=True)
    assert local.returncode == 0 and not local.stderr and json.loads(local.stdout)['device_accessed'] is False
    result = {'passed': True, 'affected_cases': len(cases), 'cases': cases, 'unchanged_functions': unchanged,
              'tested_files': {name: sha((HERE / name).read_bytes()) for name in ('device.py', 'irq-evidence.py', 'test-irq.py')},
              'default_check_returncode': 0, 'saved_fixture_source_sha256': sha(f.ORIGINAL.read_bytes()),
              'cohort_delivery_sha256': sha((cohort_leaf / 'delivery.json').read_bytes()),
              'synthetic_IRQ_counts_and_new_cohort_identity': True, 'runtime_request_generated': False,
              'old_suites_rerun': False, 'device_SSH_USB_build_SDK_Git': False}
    (HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'affected_cases': len(cases), 'unchanged_functions': len(unchanged)}))


if __name__ == '__main__':
    main()
