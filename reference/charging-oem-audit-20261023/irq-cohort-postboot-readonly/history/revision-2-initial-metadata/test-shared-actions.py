"""R2 only: the independent shared-action counterexample and new permutations."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def functions(path):
    source = path.read_text()
    return {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}


def main():
    spec = importlib.util.spec_from_file_location('irq_revision2', HERE / 'irq-evidence.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    base = ' CPU0 CPU1\n47: 0 0 pmic_arb 135940 Edge usbin-plugin\n48: 0 0 pmic_arb 135942 Edge usbin-src-change\n'
    cases = []
    for action in ('usbin-plugin, unrelated-action', 'unrelated-action, usbin-plugin',
                   'usbin-plugin,unrelated-action', 'unrelated-action,usbin-plugin',
                   'usbin-src-change, unrelated-action', 'usbin-plugin, usbin-src-change',
                   'usbin-plugin unrelated-action'):
        try:
            m.parse_interrupts(base + '49: 0 0 GICv3 123 Level ' + action + '\n')
        except ValueError:
            cases.append({'action_suffix': action, 'rejected': True})
        else:
            raise AssertionError(action)
    assert set(m.parse_interrupts(base)['named']) == set(m.NAMES)
    cases.append({'unique_original_registrations': True})
    assert set(m.parse_interrupts(base + '49: 0 0 GICv3 123 Level unrelated-action\n')['named']) == set(m.NAMES)
    cases.append({'unrelated_IRQ_ignored': True})
    # Source tokens that only contain a target substring are not that action.
    assert set(m.parse_interrupts(base + '49: 0 0 GICv3 123 Level prefix-usbin-plugin-extra\n')['named']) == set(m.NAMES)
    cases.append({'target_substring_is_not_exact_action': True})
    embedded = functions(HERE / 'device.py')
    helper = functions(HERE / 'irq-evidence.py')
    old = functions(HERE / 'history/revision-1/device.py')
    assert all(embedded[name] == source for name, source in helper.items())
    assert [name for name in old if old[name] != embedded[name]] == ['parse_interrupts']
    local = subprocess.run(['python3', '-B', str(HERE / 'device.py'), '--check-local'], capture_output=True)
    assert local.returncode == 0 and not local.stderr and json.loads(local.stdout)['device_accessed'] is False
    result = {'passed': True, 'revision': 2, 'new_affected_cases': len(cases), 'cases': cases,
              'only_changed_function': 'parse_interrupts', 'embedded_helper_exact': True,
              'default_check_returncode': 0,
              'original_27_reused_not_rerun': True,
              'original_27_receipt_sha256': sha(HERE / 'history/revision-1/test-result.json'),
              'review_counterexample_sha256': '603ddb0157b85d201651e5b71d6cf757b6a395a63d072df258be2bdf3b973fe5',
              'files': {name: sha(HERE / name) for name in ('device.py', 'irq-evidence.py', 'test-shared-actions.py')},
              'device_or_transport_or_build': False}
    (HERE / 'shared-actions-test-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'new_affected_cases': len(cases), 'old_27_rerun': False}))


if __name__ == '__main__':
    main()
