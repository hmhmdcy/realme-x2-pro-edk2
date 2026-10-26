"""Actual candidate request/command/classify/audit tests with filesystem fakes."""
from pathlib import Path
import ast
import copy
import difflib
import errno
import hashlib
import json
import runpy
import types

HERE = Path(__file__).resolve().parent
counts = {'service': 0, 'classification': 0, 'audit': 0, 'parser': 0}


def normal(seconds=100):
    return dict(shadow=0, valid=1, online=1, protection_ok=1, budget_ua=100000,
                temp_decic=250, pack_uv=8600000, cell1_uv=4300000, cell2_uv=4300000,
                fault=0, session_seconds=seconds, desired_enable=1, error=0,
                stop_error=0, latched=0, source_inhibit=0, age_ms=0, flags=0,
                cycle_timeout=0, gauge_charge_stop=0, logical_full=0,
                full_holding=0, hold_requested=0, full_cause=0, gauge_current_ua=50000)


def full():
    value = normal(0)
    value.update(desired_enable=0, logical_full=1, full_holding=1,
                 hold_requested=1, full_cause=1)
    return value


def gauge_stop():
    value = normal()
    value.update(desired_enable=0, error=-errno.EAGAIN, flags=0x4000, gauge_charge_stop=1)
    return value


class FakePath:
    def __init__(self, environment, path):
        self.environment, self.path = environment, str(path)

    def __truediv__(self, name):
        return FakePath(self.environment, self.path.rstrip('/') + '/' + str(name))

    @property
    def name(self):
        return self.path.rsplit('/', 1)[-1]

    def mkdir(self, **kwargs):
        self.environment.directories.append((self.path, kwargs))

    def read_text(self):
        if self.path == '/proc/sys/kernel/random/boot_id':
            return 'fake-same-boot\n'
        if self.path == '/sys/module/samurai_mp2650/parameters/control':
            return 'Y\n'
        raise AssertionError('unexpected read: ' + self.path)

    def resolve(self):
        assert self.name == 'driver'
        return FakePath(self.environment, '/sys/bus/i2c/drivers/samurai-mp2650')

    def exists(self):
        return True

    def write_text(self, value):
        env = self.environment
        env.writes.append((self.name, value))
        if self.name == 'charge_behaviour':
            env.auto_requested = value == 'auto'
        if value != 'inhibit-charge' and env.error_errno is not None:
            if env.error_only is None or env.error_only == self.name:
                raise OSError(env.error_errno, 'simulated real sysfs errno')
        return len(value)


class Environment:
    def __init__(self, sample, error_errno=errno.EAGAIN, error_only=None):
        self.telemetry = sample
        self.error_errno, self.error_only = error_errno, error_only
        self.writes, self.directories, self.loads = [], [], []
        self.auto_requested = False

    def path(self, value):
        return FakePath(self, value)

    def functions(self):
        source = (HERE / 'samurai-charging.py').read_text()
        tree = ast.parse(source)
        names = ['safe_gauge_charge_stop', 'request', 'inhibit', 'command']
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        assert len(nodes) == len(names)
        live = types.SimpleNamespace(CLIENT=self.path('/device'), PSY=self.path('/power'),
                                     registers=lambda: {'08': 8})
        scope = dict(errno=errno, live=live, Path=self.path, STATE=self.path('/state'),
                     time=types.SimpleNamespace(sleep=lambda seconds: None),
                     sample=lambda: dict(self.telemetry),
                     load_module=lambda meta, name, args: self.loads.append((name, args)))
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(HERE / 'samurai-charging.py'), 'exec'), scope)
        return scope


def check_service(snapshot, number, expected, *, only=None):
    counts['service'] += 1
    env = Environment(snapshot, number, only)
    scope = env.functions()
    try:
        result = scope['command']({}, 'resume')
    except OSError as error:
        assert not expected and error.errno == number
        assert not env.auto_requested and ('charge_behaviour', 'inhibit-charge') in env.writes
    else:
        assert expected and result['requested'] == 'auto' and env.auto_requested
        assert ('charge_behaviour', 'inhibit-charge') not in env.writes
        assert env.loads == [('samurai-usb-input', ['register_board=1']),
                             ('samurai-gauge-protection', ['register_board=1']),
                             ('samurai-mp2650', ['runtime_board=1', 'control=1'])]
    return env


# A real EAGAIN with every exact safe-stop predicate retains the actual AUTO
# request even though all three property writes report policy acquisition hold.
check_service(gauge_stop(), errno.EAGAIN, True)
source = normal()
source.update(valid=0, protection_ok=0, source_inhibit=1, desired_enable=0,
              error=-errno.ENODATA, age_ms=-1)
check_service(source, errno.ENODATA, True)
check_service(normal(), None, True)
check_service(full(), None, True)
for key, value in [('latched', 1), ('stop_error', -errno.EREMOTEIO), ('fault', 1),
                   ('protection_ok', 0), ('valid', 0), ('online', 0),
                   ('cycle_timeout', 1), ('age_ms', 3001), ('flags', 0xc000),
                   ('gauge_charge_stop', 0), ('desired_enable', 1)]:
    sample = gauge_stop(); sample[key] = value
    check_service(sample, errno.EAGAIN, False)
for number in [errno.EIO, errno.ETIMEDOUT, errno.ERANGE, errno.EPERM]:
    # Inject at AUTO after the earlier limit writes succeeded. The production
    # command's real exception path must inhibit and cancel the request.
    check_service(gauge_stop(), number, False, only='charge_behaviour')
check_service(source, errno.EIO, False)
old_timeout = dict(source, cycle_timeout=1, error=-errno.ETIME)
check_service(old_timeout, errno.ENODATA, False)

health = runpy.run_path(str(HERE / 'charging-health.py'))
classify, audit, parse = (health[name] for name in ['classify', 'audit', 'parse_telemetry'])
service_predicate = Environment(gauge_stop()).functions()['safe_gauge_charge_stop']


def classification(snapshot, expected):
    counts['classification'] += 1
    assert classify(snapshot) == expected
    assert health['safe_gauge_charge_stop'](snapshot) == service_predicate(snapshot)


classification(normal(), 'managed')
classification(full(), 'full_holding')
classification(gauge_stop(), 'waiting_gauge')
classification(source, 'waiting_source')
for key, value, expected in [
        ('latched', 1, 'fault'), ('fault', 1, 'fault'), ('stop_error', -5, 'fault'),
        ('error', -errno.EIO, 'fault'), ('cycle_timeout', 1, 'fault'),
        ('full_holding', 0, 'unavailable'), ('hold_requested', 0, 'unavailable'),
        ('full_cause', 99, 'unavailable'), ('desired_enable', 1, 'unavailable'),
        ('session_seconds', 5, 'unavailable'), ('age_ms', 3001, 'stale'),
        ('valid', 0, 'unavailable'), ('protection_ok', 0, 'unavailable'),
        ('flags', 0x4000, 'fault')]:
    sample = full(); sample[key] = value
    classification(sample, expected)
classification(dict(gauge_stop(), latched=1), 'fault')
classification(dict(gauge_stop(), cycle_timeout=1), 'fault')
classification(dict(normal(), session_seconds=-1), 'fault')
classification(dict(normal(), session_seconds=36000), 'fault')


def row(snapshot, status='Not charging'):
    return {'telemetry': snapshot, 'state': 'managed', 'charger_status': status}


def check_audit(rows, passed, regressions=0, boundaries=None, mutate=None):
    counts['audit'] += 1
    data = dict(samples=rows, same_boot=True, taint_before=0, taint_after=0,
                limits_before={'input': 100000}, limits_after={'input': 100000},
                native_allowance_before=100000, native_allowance_after=100000,
                fault_delta={'Oops:': 0}, camera_and_four_services_unchanged=True,
                duration_seconds=120, manifest_sha256='candidate-manifest')
    if mutate:
        data.update(mutate)
    result = audit(data)
    assert result['passed'] == passed, result
    assert result['session_counter_regressions'] == regressions, result
    if boundaries is not None:
        assert result['verified_full_boundaries'] == boundaries, result
    return result


check_audit([row(normal(100)), row(normal(110))], True, boundaries=0)
check_audit([row(normal(100)), row(full()), row(full()), row(normal(0)), row(normal(5))],
            True, boundaries=1)
check_audit([row(full()), row(full())], True, boundaries=1)
check_audit([row(normal(100)), row(normal(1))], False, regressions=1)
check_audit([row(normal(100)), row(normal(1), 'Full')], False, regressions=1)
check_audit([row(normal(100)), row(normal(0), 'Full')], True, boundaries=1)
check_audit([row(normal(100)), row(dict(full(), full_holding=0))], False, regressions=1)
check_audit([row(normal(100)), row(dict(full(), full_cause=99))], False, regressions=1)
check_audit([row(normal(100)), row(dict(full(), cycle_timeout=1))], False, regressions=1)
check_audit([row(normal(100)), row(dict(full(), error=-errno.EIO))], False, regressions=1)
gauge_result = check_audit([row(normal()), row(gauge_stop())], False)
assert gauge_result['state_counts']['waiting_gauge'] == 1 and not gauge_result['state_counts']['fault']
check_audit([row(normal()), row(source)], False)
for key, value in [('latched', 1), ('protection_ok', 0), ('flags', 0xc000)]:
    sample = full(); sample[key] = value
    check_audit([row(normal()), row(sample)], False, regressions=1)
# A forged/stale saved state label cannot convert an arbitrary counter rollback
# into a Full boundary; audit recomputes directly from actual telemetry.
fake = row(normal(1)); fake['state'] = 'full_holding'
check_audit([row(normal(100)), fake], False, regressions=1)
check_audit([row(normal()), {'state': 'full_holding'}], False)
check_audit([row(normal(100)), row(source), row(normal(1))], False, regressions=1)
for key, value in [('same_boot', False), ('taint_after', 1),
                   ('camera_and_four_services_unchanged', False),
                   ('fault_delta', {'Oops:': 1}), ('limits_after', {'input': 500000})]:
    check_audit([row(full()), row(full())], False, mutate={key: value})

text = ' '.join('{}={}'.format(k, v) for k, v in full().items())
counts['parser'] += 1
assert parse(text) == full()
for bad in [text + ' valid=1', text.replace('stop_error=0', '')]:
    counts['parser'] += 1
    try:
        parse(bad)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid telemetry parsed')

names = ['samurai-charging.py', 'charging-health.py']
baseline = json.loads((HERE / 'baseline.json').read_text())
production = HERE.parent.parent.parent / 'charging-management-20261023'
main_unchanged = {name: hashlib.sha256((production / name).read_bytes()).hexdigest() == digest
                  for name, digest in baseline.items()}
assert all(main_unchanged.values())
kernel_receipt = json.loads((HERE.parent / 'test-result.json').read_text())
kernel_unchanged = {name: hashlib.sha256((HERE.parent / name).read_bytes()).hexdigest() == digest
                    for name, digest in kernel_receipt['candidate_files'].items()}
assert all(kernel_unchanged.values())
patch = ''.join(''.join(difflib.unified_diff((HERE / 'baseline' / name).read_text().splitlines(True),
                    (HERE / name).read_text().splitlines(True),
                    fromfile='a/' + name, tofile='b/' + name)) for name in names)
(HERE / 'userspace.patch').write_text(patch)
report = {'passed': True, 'cases': counts,
          'candidate_files': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in names},
          'baseline': baseline, 'main_unchanged': main_unchanged,
          'frozen_kernel_unchanged': kernel_unchanged,
          'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'patch_sha256': hashlib.sha256(patch.encode()).hexdigest(),
          'scope': 'Actual service request/inhibit/command AST bodies and full health module functions; fake filesystem and telemetry',
          'phone_accessed': False, 'sdk_accessed': False, 'kernel_candidate_modified': False}
(HERE / 'test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
