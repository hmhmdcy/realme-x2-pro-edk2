"""PC-only491 preparation/cache regression; never calls the target callback.

All inputs are retained files on the PC. Does not mount/access WSL or the SDK.
Writes a fresh private probe-local-NNN receipt, retaining failed attempts.
"""
from pathlib import Path
import ast
import hashlib
import json
import runpy
import sys
import traceback
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('E:/edk2-samurai-out')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inert_import(path):
    tree = ast.parse(path.read_text())
    assert all(isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign, ast.Expr)) for node in tree.body)
    for node in tree.body:
        if isinstance(node, ast.Expr):
            assert isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        if isinstance(node, ast.Assign):
            for sub in ast.walk(node.value):
                if isinstance(sub, ast.Call):
                    assert isinstance(sub.func, ast.Name) and sub.func.id == 'Path'
    # Windows has no pwd; import-only stub is never used to invoke run().
    previous = sys.modules.get('pwd')
    if previous is None:
        sys.modules['pwd'] = types.ModuleType('pwd')
    try:
        return runpy.run_path(str(path))
    finally:
        if previous is None:
            del sys.modules['pwd']


def protocol(auditor, path, model):
    text = path.read_text()
    result = auditor['one'](text, 'GST_RESULT')
    images = auditor['rows'](text, 'GST_IMAGE')
    assert len(images) == int(result['frames']) and result['result'] == result['bus-errors'] == '0'
    observations, queues, receipts, history, numeric, numeric_receipts, revision = auditor['audit_history'](text)
    delivered = {int(row['sequence']) for row in images}
    domains = auditor['audit_domains'](text, model, int(result['width']), int(result['height']),
        observations, queues, receipts, numeric, numeric_receipts, delivered)
    return dict(path=str(path), sha256=sha(path), model=model, result=result,
                history=history, queues=len(queues), numerical_commits=revision,
                stop_receipts=[row for row in receipts.values() if row['success'] == '0'],
                unresolved_tokens=sorted(set(observations)-set(receipts)), protocol=domains)


def main():
    output = PRIVATE / 'kernel491'
    output.mkdir(exist_ok=True)
    number = 1
    while (output / f'probe-local-{number:03d}.json').exists():
        number += 1
    receipt = output / f'probe-local-{number:03d}.json'
    report = dict(stage=491, passed=False, scope='PC-only preparation and actual retained-log parser regression',
                  target_callback_executed=False, target_or_sdk_access=False, full_audits=[], protocol_only=[])
    try:
        callback = inert_import(HERE / 'default-probe.py')
        auditor = inert_import(HERE / 'probe-log-audit.py')
        ast.parse(Path(__file__).read_text())
        report['source_sha256'] = {name: sha(HERE/name) for name in ['default-probe.py', 'probe-log-audit.py', 'validate-probe-local.py']}
        tools = {'pipeline-fixture': PRIVATE/'kernel449/pipeline-fixture-long',
                 'gst-sustained': PRIVATE/'kernel449/gst-sustained',
                 'user-launcher.py': HERE.parent/'kernel486/user-launcher.py'}
        assert all(sha(path) == callback['TOOLS'][name] for name, path in tools.items())
        report['tools'] = {name: dict(path=str(path), sha256=sha(path)) for name, path in tools.items()}
        cases = [dict(name=f'{model}-640x480-native', model=model, width=640, height=480, frames=12, isolated=False)
                 for model in ['s5kgw1', 'imx319', 's5k3m5', 'imx471']]
        cases += [dict(name=f's5kgw1-{width}x{height}-'+('isolated' if isolated else 'native'), model='s5kgw1',
                       width=width, height=height, frames=12, isolated=isolated)
                  for width, height in [(1280, 720), (1920, 1080)] for isolated in [False, True]]
        callback['checked_cases'](cases)
        report['accepted_case_schema'] = cases
        helper = (HERE.parent/'kernel449/gst-sustained.c').read_text()
        assert 'argc!=4' in helper and 'n<12||n>10000' in helper
        report['helper_source_sha256'] = sha(HERE.parent/'kernel449/gst-sustained.c')
        report['frames_policy'] = 'plan12, accepted finite12..32; no automatic extension or retry; helper actual minimum12'
        base = PRIVATE/'kernel481/runtime-collected-r1/default-probe-forward-first'
        old = json.loads((base/'probe-report-private.json').read_text())
        for case in cases[:4]:
            model = case['model']; name = model+'-gst'; path = base/name/'client.log'
            previous = old['cases'][name]
            text = path.read_text()
            checked = auditor['audit'](text, model=model, width=640, height=480, frames=32,
                before=previous['idle_before']['status'], after=previous['idle_after']['status'], require_fixed_warnings=False)
            assert checked['protocol']['first_twelve_delivered_math_sofs']
            try:
                auditor['audit'](text, model=model, width=640, height=480, frames=32,
                    before=previous['idle_before']['status'], after=previous['idle_after']['status'])
            except AssertionError:
                assert any(checked['warnings']['target_counts'].values())
            else:
                raise AssertionError('Old target-warning log unexpectedly passed the491 warning gate')
            report['full_audits'].append(dict(path=str(path), sha256=sha(path), old_target_warning_gate_rejected=True, result=checked))
        base = PRIVATE/'kernel474/runtime-collected-r1'
        for name in ['1920x1080-native', '1920x1080-isolated']:
            #474 retained total counters, not case-local before/after. Do not
            # invent those snapshots merely to call the complete audit.
            checked = protocol(auditor, base/name/'client.log', 's5k3m5')
            checked['cached_branch'] = name
            report['protocol_only'].append(checked)
        for model in ['s5kgw1', 'imx319', 's5k3m5', 'imx471']:
            path = PRIVATE/'kernel440/install-collected-r2'/f'gst-{model}.log'
            text = path.read_text()
            observations, queues, receipts, history, numeric, numeric_receipts, revision = auditor['audit_history'](text)
            assert auditor['one'](text, 'GST_RESULT')['frames'] == '12' and revision > 0
            report['protocol_only'].append(dict(path=str(path), sha256=sha(path), model=model,
                scope='history only: this older GST helper did not log consumer sequence; no fabricated SOF association',
                history=history, numerical_commits=revision,
                negative_receipts=[row for row in receipts.values() if row['success'] == '0'],
                unresolved_tokens=sorted(set(observations)-set(receipts))))
        report['protocol_only'].append(protocol(auditor,
            PRIVATE/'kernel467/runtime-collected-r1/1280x720-isolated/client.log', 's5k3m5'))
        # A few join-breaking corruptions exercise the added protocol gates.
        # Only memory copies are changed; every original cache stays byte exact.
        original_path = PRIVATE/'kernel481/runtime-collected-r1/default-probe-forward-first/s5kgw1-gst/client.log'
        original_text = original_path.read_text()
        import re
        mutations = {
            'receipt_trace': re.sub(r'(IPE_RECEIPT [^\n]* trace=)\d+', r'\g<1>0', original_text, count=1),
            'gtm_source_histogram': re.sub(r'(IPE_TONE_PREPARE [^\n]* gtm-source-histogram=)\d+', r'\g<1>0', original_text, count=1),
            'known_wb_context': re.sub(r'(WB context [^\n]* known=)1', r'\g<1>0', original_text, count=1),
        }
        report['in_memory_negative_checks'] = []
        previous = old['cases']['s5kgw1-gst']
        for name, changed in mutations.items():
            assert changed != original_text
            try:
                auditor['audit'](changed, model='s5kgw1', width=640, height=480, frames=32,
                    before=previous['idle_before']['status'], after=previous['idle_after']['status'], require_fixed_warnings=False)
            except AssertionError:
                report['in_memory_negative_checks'].append(dict(name=name, rejected=True))
            else:
                raise AssertionError('Broken protocol join was accepted: '+name)
        # A real isolated720 cache covers the geometry/protocol. Actual live
        #491 identities and the new main720/1080 combination remain untested.
        report['limitations'] = ['No full callback/launcher execution or hardware access',
            'Old caches retain old warnings; only strict warning rejection is expected',
            'High-resolution protocol audits use retained tele1080 native/isolated and tele720 isolated; no case-local hardware counter closure for those old caches',
            'No fabricated/truncated twelve-frame success run;440 twelve-frame history lacks consumer sequence,481 first12 actual delivered math membership retained',
            'Live map-inode/pwd/isolated-worker/lease sampling awaits authorized491 hardware receipts']
        report['passed'] = True
    except BaseException:
        report['failure'] = traceback.format_exc()
        raise
    finally:
        receipt.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(dict(receipt=str(receipt), sha256=sha(receipt), passed=report['passed'], failure=report.get('failure'))))


if __name__ == '__main__':
    main()
