"""Exercise actual R8 fetch receipts against private temporary filesystem fixtures."""
from pathlib import Path
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r8_launcher', HERE / 'run-r8-update.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
TRANSACTION = 'charging-update-r8'
WORKER = '/root/charging-management-20261023/charging-update-r8-runner.py'
REQUEST = dict(transaction=TRANSACTION, worker_sha256='a' * 64, expected_boot='fixture-boot')
cases = []


def fetch_fixture(expected, *, process=True, receipt=True, ticks='12345',
                  state='S', argv=None, receipt_hash=None):
    with tempfile.TemporaryDirectory(prefix='r8-fetch-') as tmp:
        root = Path(tmp)
        base = root / 'root/charging-management-20261023/charging-update-r8-runner'
        base.parent.mkdir(parents=True)
        if receipt:
            base.with_suffix('.pid-private.json').write_text(json.dumps(dict(
                pid=123, startticks='12345', worker=str(base.with_suffix('.py')), transaction=TRANSACTION,
                worker_sha256=receipt_hash or REQUEST['worker_sha256'], boot_id=REQUEST['expected_boot'])))
        if process:
            proc = root / 'proc/123'
            proc.mkdir(parents=True)
            (proc / 'stat').write_text('123 (python3) ' + ' '.join([state] + ['0'] * 18 + [ticks]))
            if argv is None:
                argv = ['python3', '-B', str(base.with_suffix('.py')), '--execute-r8']
            (proc / 'cmdline').write_bytes(b'\0'.join(x.encode() for x in argv) + (b'\0' if argv else b''))

        def local_path(*args):
            requested = Path(*args)
            assert requested.is_absolute()
            assert requested.parts[:3] == ('/', 'root', 'charging-management-20261023') or requested.parts[:2] == ('/', 'proc')
            return root / requested.relative_to('/')

        incoming = io.TextIOWrapper(io.BytesIO(json.dumps(REQUEST).encode()))
        output = io.StringIO()
        try:
            with patch('pathlib.Path', local_path), patch.object(sys, 'stdin', incoming), contextlib.redirect_stdout(output):
                exec(compile(launcher.FETCH, '<actual-r8-fetch>', 'exec'), {})
        except AssertionError:
            assert expected == 'reject-receipt'
        else:
            assert json.loads(output.getvalue())['process_state'] == expected
        cases.append(expected)


fetch_fixture('alive')
fetch_fixture('pid_reused', ticks='54321')
fetch_fixture('exited_zombie', state='Z', argv=[])
fetch_fixture('unknown', argv=['unrelated-executable'])
fetch_fixture('absent', process=False)
fetch_fixture('launch_outcome_unknown', process=False, receipt=False)
fetch_fixture('reject-receipt', receipt_hash='b' * 64)
compile(launcher.LAUNCH, '<actual-r8-launch>', 'exec')
result = dict(passed=True, actual_fetch_cases=len(cases), cases=cases,
              launcher_sha256=hashlib.sha256((HERE / 'run-r8-update.py').read_bytes()).hexdigest(),
              actual_fetch_source_sha256=hashlib.sha256(launcher.FETCH.encode()).hexdigest(),
              phone_accessed=False, ssh_executed=False)
(HERE / 'r8-launcher-test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
