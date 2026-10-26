"""Candidate for one NEW, explicitly dispatched charging PM transaction.

Import is inert. Never launch this to inspect or resume an old transaction.
The root chat owns phone/camera/BT window coordination, not this worker.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import runpy
import subprocess
import time
import types
import uuid

PRIMITIVE_SHA256 = 'fd3fd4bef1e04dc8a29b5240cad8989d700021e353e081c0fcf0b297e4bda0a1'
CAMERA = ['ac10000.icp', 'acb3000.camss', 'ac4a000.cci', 'ac4b000.cci']
SERVICES = ['phoc', 'phosh', 'pipewire', 'wireplumber']
FAULTS = ['WARNING:', 'Oops:', 'refcount_t: underflow', 'gpu fault:', 'NGD resume failed']


class PreflightRejected(RuntimeError):
    pass


def load_reviewed(path, digest, name):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(name + ' hash differs from reviewed source')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module


def validate_config(c):
    if not c.get('execute') or not c.get('window_confirmed'):
        raise ValueError('explicit execute and root-confirmed exclusive window required')
    if not re.fullmatch(r'charging-pm-[a-z0-9][a-z0-9-]{0,40}', c['transaction']):
        raise ValueError('invalid new transaction name')
    if c['transaction'] == 'charging-pm-r5':
        raise ValueError('old r5 cannot be reused')
    if str(uuid.UUID(c['boot_id'])) != c['boot_id']:
        raise ValueError('invalid expected boot identity')
    for name in ['manifest_sha256', 'live_sha256', 'previous_receipt_sha256']:
        if not re.fullmatch(r'[a-f0-9]{64}', c[name]):
            raise ValueError('invalid reviewed digest: ' + name)
    if not c['release'] or not Path(c['output_root']).is_absolute():
        raise ValueError('release and absolute output root required')


def healthy(s):
    # This classifies a fresh sample only; every other PM acceptance gate stays
    # independent. A normal Full is charge-only hold, never operator INHIBIT.
    common = (all(s.get(k) == 1 for k in ['valid', 'online', 'protection_ok'])
              and s.get('shadow') == 0 and 0 <= s.get('age_ms', -1) < 2000
              and s.get('budget_ua', 0) >= 50000
              and all(s.get(k) == 0 for k in ['error', 'stop_error', 'latched', 'source_inhibit', 'fault']))
    if not common:
        return False
    if s.get('desired_enable') == 1:
        return True  # Existing managed sample contract.
    return (s.get('desired_enable') == 0
            and all(s.get(k) == 1 for k in ['logical_full', 'hold_requested', 'full_holding'])
            and type(s.get('full_cause')) is int and s['full_cause'] in [1, 2, 3]
            and s.get('session_seconds') == 0
            and s.get('gauge_charge_stop') == 0 and s.get('cycle_timeout') == 0
            and type(s.get('flags')) is int and 0 <= s['flags'] <= 0xffff
            and not s['flags'] & 0xc000)


def services(state):
    return {name: sorted((p['pid'], p['uid']) for p in state['services'] if p['comm'] == name)
            for name in SERVICES}


def configuration_preserved(before, after):
    old = {k: v for k, v in before['state']['registers'].items() if k != '13'}
    new = {k: v for k, v in after['state']['registers'].items() if k != '13'}
    if old == new:
        return True
    # A newly established safe Full may clear only CHG_EN. Input converter,
    # all limits and every other register bit must match the managed baseline.
    first, last = before['sample'], after['sample']
    if not (healthy(first) and first.get('desired_enable') == 1
            and healthy(last) and last.get('desired_enable') == 0):
        return False
    a, b = old.get('08'), new.get('08')
    if not (type(a) is int and type(b) is int and a & 0x18 == 0x10 and b & 0x18 == 0):
        return False
    old['08'] = a & ~0x10
    return old == new


def preflight(c, before):
    reasons = []
    for key, expected in [('boot_id', c['boot_id']), ('release', c['release']),
                          ('manifest_sha256', c['manifest_sha256'])]:
        if before.get(key) != expected:
            reasons.append('identity mismatch: ' + key)
    state = before['state']
    if state.get('taint') != '0' or state.get('driver') != 'samurai-mp2650':
        reasons.append('charger driver or taint')
    if not all(state.get('camera_pm', {}).get(name) == 'suspended' for name in CAMERA):
        reasons.append('camera not suspended')
    m2m = json.loads(state.get('m2m', '{}'))
    if not all(m2m.get(k) == v for k, v in {'users': 0, 'running': False, 'fatal': False,
                                          'pinned': False, 'orphans': 0, 'first_error': 0}.items()):
        reasons.append('camera resource state not idle')
    if not all(len(rows) == 1 and rows[0][1] == 10000 for rows in services(state).values()):
        reasons.append('four user services not established')
    if not healthy(before.get('sample', {})):
        reasons.append('charging baseline unhealthy')
    if not before.get('modules_exact') or not before.get('read_only_prerequisites'):
        reasons.append('module/prerequisite evidence incomplete')
    old = before.get('previous', {})
    if not (old.get('receipt_valid') is True and old.get('process_state') in ['absent', 'pid_reused']):
        reasons.append('previous r5 terminal/restoration/process exit unproven')
    return reasons


def audit_trace(text):
    starts = re.compile(r'\s(\d+\.\d+): device_pm_callback_start: (\S+) (\S+), parent: [^,]+, ([^\[]*)\[([^\]]+)\]')
    ends = re.compile(r'\s(\d+\.\d+): device_pm_callback_end: (\S+) (\S+), err=(-?\d+)')
    targets = ['0-005c', 'samurai-usb-input', 'samurai-gauge-protection', '5-0055']
    pending, records, errors = {}, [], []
    header = re.search(r'entries-in-buffer/entries-written:\s*(\d+)/(\d+)', text)
    if not header or header[1] != header[2] or int(header[1]) == 0:
        errors.append('trace completeness/overflow header unproven')
    for line in text.splitlines():
        m = starts.search(line)
        if m and m[3] in targets:
            key = (m[2], m[3])
            if key in pending:
                errors.append('overlapping callback: ' + m[3])
            pending[key] = {'driver': m[2], 'device': m[3], 'ops': m[4].strip(),
                            'phase': m[5], 'start': float(m[1])}
        m = ends.search(line)
        if m and m[3] in targets:
            key = (m[2], m[3])
            row = pending.pop(key, None)
            if row is None:
                errors.append('unmatched callback end: ' + m[3])
            else:
                records.append({**row, 'end': float(m[1]), 'error': int(m[4])})
    if pending:
        errors.append('unfinished callbacks')
    selected = {}
    for device in targets:
        for phase in ['suspend', 'resume']:
            rows = [r for r in records if r['device'] == device and r['phase'] == phase and r['ops']]
            if len(rows) != 1 or rows[0]['error'] != 0 or rows[0]['end'] < rows[0]['start']:
                errors.append('missing/failed callback: ' + device + '/' + phase)
            else:
                selected[device, phase] = rows[0]
    if not errors:
        for device in targets[1:]:
            if not (selected['0-005c', 'suspend']['end'] <= selected[device, 'suspend']['start']
                    and selected[device, 'resume']['end'] <= selected['0-005c', 'resume']['start']):
                errors.append('supplier order: ' + device)
    return {'passed': not errors, 'errors': errors, 'callbacks': records}


def classify(c, before, primitive, after, trace, cleanup):
    trace_result = audit_trace(trace)
    checks = {'primitive_returned': primitive.get('outcome') == 'returned' and primitive.get('mem_returned') is True,
              'primitive_cleanup_safe': primitive.get('cleanup') == 'alarm_already_consumed_or_cleared' and not primitive.get('cleanup_error'),
              'actual_residency': 1 <= primitive.get('estimated_residency_seconds', -1) <= 20,
              'trace_complete_and_ordered': trace_result['passed'], 'trace_cleanup_safe': cleanup.get('passed') is True}
    if after is None:
        checks['post_evidence_complete'] = False
    else:
        checks.update(same_boot=after.get('boot_id') == before.get('boot_id') == c['boot_id'],
                      manifest_unchanged=after.get('manifest_sha256') == before.get('manifest_sha256') == c['manifest_sha256'],
                      modules_exact=after.get('modules_exact') is True,
                      release_and_driver_preserved=after.get('release') == c['release'] and after['state'].get('driver') == 'samurai-mp2650',
                      charging_resumed_healthy=healthy(after.get('sample', {})),
                      rtc_irq_once=after.get('rtc_irq', -1) - before.get('rtc_irq', -1) == 1,
                      rtc_was_wakeup_irq=after.get('wakeup_irq') == before.get('rtc_irq_number') and type(after.get('wakeup_irq')) is int,
                      same_camera=after['state'].get('camera_pm') == before['state'].get('camera_pm') and after['state'].get('m2m') == before['state'].get('m2m'),
                      same_four_services=services(after['state']) == services(before['state']),
                      taint_zero=after['state'].get('taint') == '0',
                      charger_config_preserved=configuration_preserved(before, after),
                      native_allowance_preserved=after.get('allowance') == before.get('allowance') and type(after.get('allowance')) is int and after['allowance'] >= 50000,
                      no_new_faults=after['dmesg'].startswith(before['dmesg']) and all(x not in after['dmesg'][len(before['dmesg']):] for x in FAULTS))
        stats_a, stats_b = before.get('stats', {}), after.get('stats', {})
        checks['suspend_stats_success'] = (type(stats_a.get('success')) is int and type(stats_b.get('success')) is int
                                           and stats_b['success'] - stats_a['success'] == 1
                                           and type(stats_a.get('fail')) is int and stats_b.get('fail') == stats_a['fail']
                                           and all(stats_b.get(k) == v for k, v in stats_a.items() if k.startswith('failed_')))
    return {'passed': all(checks.values()), 'checks': checks, 'trace_audit': trace_result,
            'classification': 'verified' if all(checks.values()) else 'returned_evidence_incomplete_or_failed'}


def dispatch(c, board):
    """Actual one-shot schedule. Fake boards exercise this exact function."""
    validate_config(c)
    board.create_new(c)
    result = {'terminal': True, 'passed': False, 'classification': 'preflight_rejected'}
    before = primitive = after = None
    stage = 'preflight'
    trace = ''
    cleanup = {'passed': True, 'owned': False}
    try:
        before = board.capture(c, before=True)
        board.save('before-private.json', before)
        reasons = preflight(c, before)
        board.save('preflight-result.json', {'passed': not reasons, 'reasons': reasons})
        if reasons:
            result['preflight_reasons'] = reasons
        else:
            stage = 'trace_setup'
            board.start_trace(c)
            stage = 'primitive'
            primitive = board.suspend_once()
            board.save('primitive-result.json', primitive)
            trace, cleanup = board.finish_trace()
            board.save('trace-cleanup-result.json', cleanup)
            stage = 'post_evidence'
            if primitive.get('outcome') == 'returned':
                board.wait_for_fresh_sample()
            after = board.capture(c, before=False)
            board.save('after-private.json', after)
            result.update(classify(c, before, primitive, after, trace, cleanup))
            if primitive.get('outcome') != 'returned':
                result['classification'] = 'primitive_aborted_or_failed'
    except BaseException as error:
        if stage == 'primitive':
            board.save('primitive-exception.json', {'type': type(error).__name__, 'message': str(error)})
        result.update(passed=False, classification=('preflight_rejected' if isinstance(error, PreflightRejected) else 'preflight_evidence_failed') if stage == 'preflight' else 'worker_evidence_or_operation_failed',
                      failed_stage=stage,
                      error={'type': type(error).__name__, 'message': str(error)})
    finally:
        extra = board.cleanup_trace_if_owned()
        if extra is not None:
            board.save('trace-cleanup-final.json', extra)
            if not extra.get('passed'):
                result.update(passed=False, classification='trace_cleanup_failed')
        board.save('result.json', result)
    return result


class RealBoard:
    def __init__(self, c):
        self.c = c
        self.out = self.trace = None
        self.trace_owned = False
        self.live = load_reviewed(c['live_helper'], c['live_sha256'], 'reviewed_live')
        self.pm = load_reviewed(Path(__file__).with_name('pm-transaction.py'), PRIMITIVE_SHA256, 'reviewed_pm')
        self.io = self.pm.SysfsPMIO(self.phase)

    def create_new(self, c):
        self.out = Path(c['output_root']) / c['transaction']
        self.out.mkdir(mode=0o700)  # parents must exist; never reuse a transaction
        self.trace = Path('/sys/kernel/tracing/instances') / c['transaction']

    def save(self, name, data):
        target = self.out / name
        temporary = target.with_suffix('.next')
        with temporary.open('w') as stream:
            json.dump(data, stream, indent=2); stream.flush(); os.fsync(stream.fileno())
        temporary.replace(target)

    def phase(self, entry):
        entry = {'pid': os.getpid(), **entry}
        with (self.out / 'phases-private.jsonl').open('a') as stream:
            stream.write(json.dumps(entry) + '\n'); stream.flush(); os.fsync(stream.fileno())
        self.save('phase-private.json', entry)

    def previous(self, c):
        payload = Path(c['previous_receipt']).read_bytes()
        receipt = json.loads(payload)
        valid = (hashlib.sha256(payload).hexdigest() == c['previous_receipt_sha256']
                 and receipt.get('terminal') is True and receipt.get('restored') is True
                 and receipt.get('worker_exited') is True and receipt.get('boot_id') == c['boot_id']
                 and receipt.get('transaction') == 'charging-pm-r5'
                 and receipt.get('worker_pid') == 21491
                 and receipt.get('worker_path') == '/root/charging-management-20261023/charging-pm-r5.py')
        try:
            argv = Path('/proc/21491/cmdline').read_bytes().split(bytes([0]))
            status = 'same_worker_alive' if receipt.get('worker_path', '').encode() in argv else 'pid_reused' if any(argv) else 'unknown'
        except FileNotFoundError:
            status = 'absent'
        except OSError:
            status = 'unknown'
        return {'receipt_valid': valid, 'process_state': status}

    def capture(self, c, before):
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != c['boot_id'] or os.uname().release != c['release']:
            raise ValueError('boot/release differs before hardware inspection')
        old = self.previous(c) if before else None
        if before:
            self.save('previous-transaction-result.json', old)
            if not (old['receipt_valid'] and old['process_state'] in ['absent', 'pid_reused']):
                raise PreflightRejected('previous r5 terminal/restoration/process exit unproven')
        raw = Path('/usr/share/samurai-charging/manifest.json').read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        meta = json.loads(raw)
        service = Path('/usr/sbin/samurai-charging')
        if digest != c['manifest_sha256'] or hashlib.sha256(service.read_bytes()).hexdigest() != meta['installed_files'][str(service)]:
            raise ValueError('manifest or manager identity changed')
        manager = runpy.run_path(str(service), run_name='reviewed_manager')
        if manager['verify']() != meta:
            raise ValueError('manifest changed while checking installed files')
        for name, entry in meta['modules'].items():
            manager['loaded_matches'](Path(entry['target']), name.replace('-', '_'))
        state = self.live.state()
        sample = {k: int(v) for k, v in (field.split('=') for field in (self.live.CLIENT / 'telemetry').read_text().split())}
        stats = {p.name: int(p.read_text().strip()) for p in Path('/sys/power/suspend_stats').iterdir() if p.is_file() and re.fullmatch(r'\d+', p.read_text().strip())}
        irq_line = next(row for row in Path('/proc/interrupts').read_text().splitlines() if row.endswith('pm8xxx_rtc_alarm'))
        try:
            wakeup_irq = int(Path('/sys/power/pm_wakeup_irq').read_text())
        except OSError:
            wakeup_irq = None
        prerequisites = ((Path('/sys/power/mem_sleep').read_text().strip() == '[s2idle]')
                         and Path('/sys/power/pm_wakeup_irq').exists()
                         and Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip() == 'enabled')
        if before:
            prerequisites = (prerequisites and os.geteuid() == 0
                             and not json.loads(Path('/var/lib/samurai/gnss-assist/watch-state.json').read_text())['active']
                             and all(p.read_text().strip() == 'closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
                             and all('powered=0 muted=1' in Path('/sys/bus/i2c/devices', addr, 'status').read_text() for addr in ['1-0039', '1-003a']))
        return {'boot_id': state['boot_id'], 'release': state['release'], 'manifest_sha256': digest,
                'state': state, 'sample': sample, 'stats': stats, 'rtc_irq': self.io.read_rtc_irq(),
                'rtc_irq_number': int(irq_line.split(':')[0].strip()), 'wakeup_irq': wakeup_irq,
                'allowance': int((self.live.PSY / 'samurai-usb-input/input_current_limit').read_text()),
                'modules_exact': True, 'read_only_prerequisites': prerequisites,
                'dmesg': subprocess.check_output(['dmesg'], text=True),
                'previous': old}

    def start_trace(self, c):
        self.trace.mkdir()  # fail on existing; never touch another instance
        self.trace_owned = True
        (self.trace / 'buffer_size_kb').write_text('512')
        for name in ['suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end']:
            (self.trace / 'events/power' / name / 'enable').write_text('1')
        (self.trace / 'tracing_on').write_text('1')

    def finish_trace(self):
        (self.trace / 'tracing_on').write_text('0')
        text = (self.trace / 'trace').read_text()
        (self.out / 'pm-trace-private.txt').write_text(text)
        cleanup = self.cleanup_trace_if_owned()
        return text, cleanup

    def cleanup_trace_if_owned(self):
        if not self.trace_owned:
            return None
        errors = []
        for path, value in [(self.trace / 'tracing_on', '0')] + [(self.trace / 'events/power' / name / 'enable', '0') for name in ['suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end']]:
            try:
                path.write_text(value)
            except OSError as error:
                errors.append(str(error))
        try:
            if not (self.out / 'pm-trace-private.txt').exists():
                (self.out / 'pm-trace-private.txt').write_text((self.trace / 'trace').read_text())
            self.trace.rmdir()
        except OSError as error:
            errors.append(str(error))
        self.trace_owned = False  # no automatic retry of failed cleanup
        return {'passed': not errors, 'owned': True, 'errors': errors}

    def suspend_once(self):
        return self.pm.suspend_once(self.io)

    def wait_for_fresh_sample(self):
        time.sleep(3)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--window-confirmed', action='store_true')
    for name in ['transaction', 'boot-id', 'manifest-sha256', 'release', 'output-root',
                 'live-helper', 'live-sha256', 'previous-receipt', 'previous-receipt-sha256']:
        parser.add_argument('--' + name, required=True)
    c = vars(parser.parse_args(argv))
    validate_config(c)
    os.umask(0o077)
    result = dispatch(c, RealBoard(c))
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
